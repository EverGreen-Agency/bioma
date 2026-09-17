from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_client_module, require_workspace_capability
from bioma_api.db import connect
from bioma_api.worker_bridge import generate_multichannel_insight_safe
from bioma_api.repositories import performance_social as perf_social_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.performance_social import (
    PerformanceAiSummaryInsight,
    PerformanceAiSummaryResponse,
    SocialDailyMetric,
)


def list_meta_ads(workspace_id: UUID, user: CurrentUserResponse) -> list[SocialDailyMetric]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = perf_social_repo.list_meta_ads_daily(conn, client["workspace_id"])
    return [_format_metric(row) for row in rows]


def list_linkedin_ads(workspace_id: UUID, user: CurrentUserResponse) -> list[SocialDailyMetric]:
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        rows = perf_social_repo.list_linkedin_ads_daily(conn, client["workspace_id"])
    return [_format_metric(row) for row in rows]


def generate_ai_summary(workspace_id: UUID, user: CurrentUserResponse) -> PerformanceAiSummaryResponse:
    """Insight multicanal a partir dos números reais de mídia paga.

    Até 2026-08-08 esta função montava um texto com métricas reais e
    **recomendações fixas no código** — "escalar criativos de maior retenção nos
    primeiros 3s", "concentrar orçamento em C-Level" — que não mudavam com dado
    nenhum. A tela chamava aquilo de "IA Insight". Métrica certa com conselho
    inventado é pior que só a métrica: dá autoridade a um palpite.

    Agora os números continuam vindo do banco (essa parte sempre esteve certa) e
    a LEITURA deles vai para o mesmo caminho do briefing: com `OPENAI_API_KEY`,
    o modelo sintetiza sob instrução de não afirmar nada fora dos números; sem
    chave, volta uma prévia que RELATA em vez de recomendar, rotulada como tal.

    `generation_mode` sobe para a tela justamente para ela poder dizer qual dos
    dois aconteceu — o usuário precisa saber se leu análise ou organização.
    """
    with connect() as conn:
        client = _accessible_workspace(conn, workspace_id, user)
        totals = perf_social_repo.get_multichannel_totals(conn, client["workspace_id"])

    channels = []
    for key, label in (("meta", "Meta Ads (Instagram/Facebook)"), ("linkedin", "LinkedIn Ads B2B")):
        data = totals.get(key) or {}
        spend = data.get("spend_cents") or 0
        leads = data.get("leads") or 0
        if not spend:
            # Canal sem investimento não entra: o modelo não deve ter a chance
            # de escrever sobre um canal que não rodou.
            continue
        channels.append(
            {
                "channel": f"{key}_ads",
                "label": label,
                "spend_cents": spend,
                "leads": leads,
                "clicks": data.get("clicks") or 0,
                "impressions": data.get("impressions") or 0,
                "conversions": data.get("conversions") or 0,
                "cpa_cents": int(spend / leads) if leads else 0,
            }
        )

    total_spend = sum(channel["spend_cents"] for channel in channels)
    total_leads = sum(channel["leads"] for channel in channels)
    overall_cpa = int(total_spend / total_leads) if total_leads else 0

    dossier = {
        "channels": channels,
        "total_spend_cents": total_spend,
        "total_leads": total_leads,
        "overall_cpa_cents": overall_cpa,
        "currency": "BRL",
        "note": "Valores em centavos. Nenhum benchmark externo disponível.",
    }

    try:
        result = generate_multichannel_insight_safe(dossier)
        insight = result["insight"]
        generation_mode = result["generation_mode"]
    except Exception:
        # Falha de IA não pode derrubar a tela de métricas: os números reais
        # continuam valendo. Cai na prévia e diz que caiu.
        insight = {
            "summary": (
                f"Não foi possível gerar a análise agora. Números do período: "
                f"R$ {total_spend / 100:,.2f} investidos, {total_leads} leads, "
                f"CPA de R$ {overall_cpa / 100:,.2f}."
            ),
            "insights": [],
        }
        generation_mode = "unavailable"

    return PerformanceAiSummaryResponse(
        workspace_id=workspace_id,
        generated_at=datetime.now(timezone.utc),
        summary_text=insight["summary"],
        total_spend_cents=total_spend,
        total_leads=total_leads,
        overall_cpa_cents=overall_cpa,
        generation_mode=generation_mode,
        insights=[PerformanceAiSummaryInsight(**item) for item in insight["insights"]],
    )


def _format_metric(row: dict) -> SocialDailyMetric:
    d = dict(row)
    impressions = d.get("impressions", 0)
    clicks = d.get("clicks", 0)
    spend_cents = d.get("spend_cents", 0)
    conversions = d.get("conversions", 0)
    revenue_cents = d.get("revenue_cents", 0)

    d["ctr"] = round((clicks / impressions * 100), 2) if impressions > 0 else 0.0
    d["cpc_cents"] = int(spend_cents / clicks) if clicks > 0 else 0
    d["cpa_cents"] = int(spend_cents / conversions) if conversions > 0 else 0
    d["roas"] = round((revenue_cents / spend_cents), 2) if spend_cents > 0 else 0.0
    return SocialDailyMetric(**d)


def _accessible_workspace(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    require_client_module(client, user, "analytics")
    if capability:
        require_workspace_capability(client, user, capability)
    return client
