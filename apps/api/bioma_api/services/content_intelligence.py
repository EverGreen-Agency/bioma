from datetime import date, timedelta
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.integrations.ahrefs import AhrefsClient, AhrefsError
from bioma_api.repositories import content_intelligence as repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.content_intelligence import (
    ContentRetrospectiveSummary,
    ScriptScoreboard,
    ScriptScoreboardRow,
    ContentScriptSummary,
    GenerateScriptsRequest,
    HookAnalysisSummary,
    InstagramPostSummary,
)
from bioma_api.worker_bridge import execute_squad_pipeline_safe

# Datas comemorativas de marketing recorrentes no Brasil — calendário público,
# usado só como contexto real de mercado na geração de roteiros. Curadoria
# manual e honesta: se o mês não tiver data listada, o roteiro segue sem esse
# insumo em vez de inventar uma data.
COMMEMORATIVE_DATES = {
    1: ["Ano Novo (01/01)", "Volta às aulas"],
    2: ["Carnaval (data móvel)"],
    3: ["Dia do Consumidor (15/03)", "Dia Internacional da Mulher (08/03)"],
    4: ["Páscoa (data móvel)", "Dia da Mentira (01/04)"],
    5: ["Dia das Mães (2º domingo)", "Dia do Trabalho (01/05)"],
    6: ["Festas Juninas", "Dia dos Namorados (12/06)"],
    7: ["Férias escolares de meio de ano"],
    8: ["Dia dos Pais (2º domingo)"],
    9: ["Dia do Cliente (15/09)", "Independência (07/09)"],
    10: ["Dia das Crianças (12/10)", "Mês do Halloween"],
    11: ["Black Friday (última sexta)", "Consciência Negra (20/11)"],
    12: ["Natal (25/12)", "Ano Novo (31/12)"],
}


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "content")
    return client


def list_instagram_posts(workspace_id: UUID, user: CurrentUserResponse, days: int = 90) -> list[InstagramPostSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        period_end = date.today()
        period_start = period_end - timedelta(days=days)
        rows = repo.list_recent_posts(conn, client["workspace_id"], period_start, period_end)
    return [InstagramPostSummary(**row) for row in rows]


def list_hook_bank(workspace_id: UUID, user: CurrentUserResponse) -> list[HookAnalysisSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = repo.list_hook_bank(conn, client["workspace_id"])
    return [HookAnalysisSummary(**row) for row in rows]


def list_retrospectives(workspace_id: UUID, user: CurrentUserResponse) -> ContentRetrospectiveSummary | None:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        row = repo.get_latest_retrospective(conn, client["workspace_id"])
    return ContentRetrospectiveSummary(**row) if row else None


def list_scripts(workspace_id: UUID, user: CurrentUserResponse, status_filter: str | None = None) -> list[ContentScriptSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = repo.list_scripts(conn, client["workspace_id"], status_filter)
    return [ContentScriptSummary(**row) for row in rows]


def generate_retrospective(workspace_id: UUID, user: CurrentUserResponse, period_days: int) -> ContentRetrospectiveSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        require_workspace_capability(client, user, "generate_content")
        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)
        posts = repo.list_recent_posts(conn, client["workspace_id"], period_start, period_end)

        if not posts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nenhum post orgânico sincronizado neste período. Conecte e sincronize o Instagram em Integrações antes de gerar a retrospectiva.",
            )

        input_data = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "posts": [
                {
                    "post_id": str(post["id"]),
                    "caption": post["caption"],
                    "transcript": post["transcript"],
                    "media_type": post["media_type"],
                    "reach": post["reach"],
                    "likes": post["likes"],
                    "comments": post["comments"],
                    "shares": post["shares"],
                    "saved": post["saved"],
                    "plays": post["plays"],
                }
                for post in posts
            ],
        }

    result = execute_squad_pipeline_safe(
        pilar="content_retrospective",
        squad_key="content_retrospective",
        input_context=input_data,
    )
    output = result["output_data"]

    hook_rows = []
    post_ids_in_scope = {str(post["id"]) for post in posts}
    for hook in output.get("hooks_que_funcionam", []):
        for post_id in hook.get("post_ids", []):
            if post_id not in post_ids_in_scope:
                continue
            hook_rows.append({
                "post_id": UUID(post_id),
                "source": "llm_transcript",
                "hook_text": hook.get("hook_text"),
                "hook_pattern": hook.get("padrao"),
                "effectiveness_score": None,
                "analysis_notes": hook.get("por_que_funciona"),
                "raw_output": hook,
            })
    for hook in output.get("hooks_que_nao_funcionam", []):
        for post_id in hook.get("post_ids", []):
            if post_id not in post_ids_in_scope:
                continue
            hook_rows.append({
                "post_id": UUID(post_id),
                "source": "llm_transcript",
                "hook_text": hook.get("hook_text"),
                "hook_pattern": None,
                "effectiveness_score": None,
                "analysis_notes": hook.get("por_que_nao_funciona"),
                "raw_output": hook,
            })

    with connect() as conn:
        row = repo.insert_retrospective(
            conn,
            client["workspace_id"],
            client["id"],
            period_start,
            period_end,
            len(posts),
            result["generation_mode"],
            output,
            result["token_usage"],
            result["estimated_cost_cents"],
            user.id,
        )
        repo.upsert_hook_analyses(conn, client["workspace_id"], hook_rows)

    return ContentRetrospectiveSummary(**row)


def generate_scripts(workspace_id: UUID, user: CurrentUserResponse, payload: GenerateScriptsRequest) -> list[ContentScriptSummary]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        require_workspace_capability(client, user, "generate_content")

        retrospective = repo.get_latest_retrospective(conn, client["workspace_id"])
        if not retrospective:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nenhuma retrospectiva encontrada. Gere a retrospectiva de conteúdo antes de pedir roteiros.",
            )
        hook_bank = repo.list_hook_bank(conn, client["workspace_id"], limit=30)

    market_context = {
        "commemorative_dates_next_month": COMMEMORATIVE_DATES.get(_next_month(), []),
        "competitor_snapshot": _competitor_snapshot(payload.competitor_handles),
    }

    input_data = {
        "count": payload.count,
        "retrospective": retrospective["output_data"],
        "hook_bank": [
            {
                "hook_text": hook["hook_text"],
                "hook_pattern": hook["hook_pattern"],
                "analysis_notes": hook["analysis_notes"],
                "source": hook["source"],
            }
            for hook in hook_bank
        ],
        "market_context": market_context,
    }

    result = execute_squad_pipeline_safe(
        pilar="content_script",
        squad_key="content_script",
        input_context=input_data,
    )
    scripts = result["output_data"].get("roteiros", [])
    if not scripts:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="O modelo não retornou roteiros.")

    with connect() as conn:
        rows = repo.insert_scripts(
            conn,
            client["workspace_id"],
            client["id"],
            retrospective["id"],
            result["generation_mode"],
            user.id,
            scripts,
        )
    return [ContentScriptSummary(**row) for row in rows]


def update_script(workspace_id: UUID, script_id: UUID, user: CurrentUserResponse, status_value: str | None, scheduled_for: date | None) -> ContentScriptSummary:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        require_workspace_capability(client, user, "generate_content")
        existing = repo.get_script(conn, client["workspace_id"], script_id)
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roteiro não encontrado.")

        patch: dict = {}
        if status_value is not None:
            patch["status"] = status_value
        if scheduled_for is not None:
            patch["scheduled_for"] = scheduled_for
        row = repo.update_script(conn, client["workspace_id"], script_id, patch)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roteiro não encontrado.")
    return ContentScriptSummary(**row)


def link_post_to_script(workspace_id: UUID, post_id: UUID, script_id: UUID, user: CurrentUserResponse) -> InstagramPostSummary:
    """Loop de feedback: quando um post real nasce de um roteiro gerado, o
    operador confirma o vínculo aqui — a próxima retrospectiva já lê a
    performance real desse post associada ao roteiro que o originou."""
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        require_workspace_capability(client, user, "generate_content")
        post = repo.get_post(conn, client["workspace_id"], post_id)
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado.")
        script = repo.get_script(conn, client["workspace_id"], script_id)
        if not script:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roteiro não encontrado.")
        row = repo.link_post_to_script(conn, client["workspace_id"], post_id, script_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post não encontrado.")
        repo.update_script(conn, client["workspace_id"], script_id, {"status": "published"})
    return InstagramPostSummary(**row)


def _next_month() -> int:
    today = date.today()
    return 1 if today.month == 12 else today.month + 1


def _competitor_snapshot(handles: list[str]) -> list[dict]:
    if not handles:
        return []
    settings = get_settings()
    if not settings.ahrefs_api_key:
        return [{"handle": handle, "configured": False, "note": "AHREFS_API_KEY não configurado no ambiente."} for handle in handles]

    client = AhrefsClient(settings.ahrefs_api_key)
    snapshots = []
    try:
        for handle in handles:
            try:
                channel = client.find_channel(handle)
                if not channel:
                    snapshots.append({
                        "handle": handle,
                        "configured": True,
                        "note": f"'{handle}' não está conectado como canal no workspace Ahrefs — conecte-o lá para habilitar o benchmark.",
                    })
                    continue
                period_end = date.today()
                period_start = period_end - timedelta(days=60)
                posts = client.top_posts(channel["channel_id"], period_start.isoformat(), period_end.isoformat())
                snapshots.append({
                    "handle": handle,
                    "configured": True,
                    "channel_found": True,
                    "top_posts": posts,
                })
            except AhrefsError as exc:
                snapshots.append({"handle": handle, "configured": True, "note": f"Erro ao consultar Ahrefs: {exc}"})
    finally:
        client.close()
    return snapshots


def get_script_scoreboard(workspace_id: UUID, user: CurrentUserResponse, period_days: int = 90) -> ScriptScoreboard:
    """Mede se os roteiros da IA performaram melhor que o resto da conta."""
    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        data = repo.script_performance_scoreboard(conn, client["workspace_id"], period_start, period_end)

    totals = data["totals"]

    def as_float(value):
        return float(value) if value is not None else None

    ai_reach = as_float(totals.get("ai_avg_reach"))
    other_reach = as_float(totals.get("other_avg_reach"))
    ai_engagement = as_float(totals.get("ai_avg_engagement"))
    other_engagement = as_float(totals.get("other_avg_engagement"))

    def lift(ai_value, base_value):
        # Sem base (ou base zerada) nao existe comparacao: None, nunca 0% nem 100%.
        if ai_value is None or base_value is None or base_value == 0:
            return None
        return round(((ai_value - base_value) / base_value) * 100, 1)

    return ScriptScoreboard(
        period_start=period_start,
        period_end=period_end,
        ai_posts=int(totals.get("ai_posts") or 0),
        other_posts=int(totals.get("other_posts") or 0),
        ai_avg_reach=ai_reach,
        other_avg_reach=other_reach,
        ai_avg_engagement=ai_engagement,
        other_avg_engagement=other_engagement,
        ai_avg_saved=as_float(totals.get("ai_avg_saved")),
        other_avg_saved=as_float(totals.get("other_avg_saved")),
        lift_reach_percent=lift(ai_reach, other_reach),
        lift_engagement_percent=lift(ai_engagement, other_engagement),
        per_script=[ScriptScoreboardRow(**row) for row in data["per_script"]],
    )
