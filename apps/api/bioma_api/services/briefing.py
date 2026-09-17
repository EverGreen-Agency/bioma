"""Rascunho de briefing a partir do que o Bioma já sabe do cliente.

Onboarding hoje começa com formulário em branco, apesar de existirem sinais
reais no banco (perfil, mídia paga, orgânico, busca, projetos contratados,
pesquisa de mercado do setor). Este serviço monta o dossiê desses sinais,
gera um rascunho e — sob confirmação — grava como artefato `briefing`.

O rascunho é sempre rotulado como rascunho, e `missing_sources` diz na cara o
que NÃO foi possível observar. Nenhuma fonte ausente é convertida em conclusão.
"""

from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import briefing as repo
from bioma_api.repositories import client_hub as client_hub_repo
from bioma_api.repositories import workspaces as workspaces_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.briefing import BriefingDraftResponse
from bioma_api.worker_bridge import generate_briefing_draft_safe

SOURCE_LABELS = {
    "profile": "Contexto do cliente (aba Contexto) não preenchido",
    "paid_media": "Mídia paga sem dado sincronizado nos últimos 90 dias",
    "organic_social": "Instagram orgânico não conectado ou sem posts sincronizados",
    "search_presence": "Search Console sem dado sincronizado",
    "sector_research": "Nenhuma pesquisa de mercado concluída para o setor",
    "contracted_scope": "Nenhum projeto/contrato cadastrado",
}


def build_draft(workspace_id: UUID, user: CurrentUserResponse, persist: bool = False) -> BriefingDraftResponse:
    require_platform_admin(user)

    with connect() as conn:
        client = workspaces_repo.find_accessible_client(conn, workspace_id, is_platform_admin(user), user.id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")

        workspace_uuid = client["workspace_id"]
        client_uuid = client["id"]

        profile = repo.profile(conn, workspace_uuid)
        signals = {
            "profile": profile,
            "paid_media": repo.paid_media(conn, client_uuid),
            "organic_social": repo.organic_social(conn, workspace_uuid),
            "top_posts": repo.top_posts(conn, workspace_uuid),
            "search_presence": repo.search_presence(conn, client_uuid),
            "sector_research": repo.sector_research(conn, (profile or {}).get("sector")),
            "contracted_scope": repo.contracted_scope(conn, workspace_uuid),
            "active_connections": repo.connections(conn, workspace_uuid),
        }

    missing = [SOURCE_LABELS[key] for key in SOURCE_LABELS if not signals.get(key)]
    used = [key for key in SOURCE_LABELS if signals.get(key)]

    if not used:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Nenhum sinal real disponível para este cliente: preencha o Contexto ou "
                "conecte uma integração antes de gerar o rascunho."
            ),
        )

    dossier = {
        "client_name": client["name"],
        "signals": signals,
        "missing_sources": missing,
    }

    try:
        result = generate_briefing_draft_safe(dossier)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="A geração do rascunho falhou. Tente novamente.",
        ) from exc

    artifact_id = None
    if persist:
        with connect() as conn:
            artifact_id = client_hub_repo.create_artifact(
                conn,
                organization_id=client["organization_id"],
                title=f"Briefing (rascunho gerado) — {client['name']}",
                kind="briefing",
                # Interno por padrão: rascunho de IA não vai para o cliente sem
                # alguém do time revisar e mudar a visibilidade.
                visibility="internal",
                content=_as_markdown(result["draft"], missing, result["generation_mode"]),
                url=None,
                created_by=user.id,
            )
            client_hub_repo.write_audit(
                conn,
                user.id,
                client["organization_id"],
                "briefing.draft_generated",
                {
                    "workspace_id": str(workspace_uuid),
                    "generation_mode": result["generation_mode"],
                    "sources_used": used,
                },
            )

    return BriefingDraftResponse(
        client_name=client["name"],
        generation_mode=result["generation_mode"],
        sources_used=used,
        missing_sources=missing,
        draft=result["draft"],
        artifact_id=artifact_id,
    )


def _as_markdown(draft: dict, missing: list[str], mode: str) -> str:
    lines = [
        "# Briefing (rascunho)",
        "",
        f"> Gerado automaticamente a partir dos dados já no Bioma ({'IA' if mode == 'live' else 'prévia local'}).",
        "> Rascunho de trabalho — revise antes de usar com o cliente.",
        "",
        "## Resumo",
        draft.get("summary", ""),
        "",
    ]
    if draft.get("diagnosis"):
        lines += ["## Diagnóstico (com evidência)", ""]
        for item in draft["diagnosis"]:
            lines.append(f"- **{item.get('observation')}** — {item.get('evidence')}")
        lines.append("")
    if draft.get("hypotheses"):
        lines += ["## Hipóteses (a validar)", ""]
        lines += [f"- {item}" for item in draft["hypotheses"]] + [""]
    if draft.get("recommended_focus"):
        lines += ["## Foco recomendado", ""]
        for item in draft["recommended_focus"]:
            lines.append(f"- **{item.get('focus')}** ({item.get('service')}) — {item.get('rationale')}")
        lines.append("")
    if draft.get("questions_for_client"):
        lines += ["## Perguntas para a próxima call", ""]
        lines += [f"- {item}" for item in draft["questions_for_client"]] + [""]
    combined_missing = list(dict.fromkeys(missing + (draft.get("missing_data") or [])))
    if combined_missing:
        lines += ["## O que ainda falta (não foi observado)", ""]
        lines += [f"- {item}" for item in combined_missing]
    return "\n".join(lines)
