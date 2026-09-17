from typing import Any
from uuid import UUID

from bioma_worker.google_client import GoogleApiClient
from bioma_worker.storage import save_gtm_snapshot


SCOPE = ("https://www.googleapis.com/auth/tagmanager.readonly",)


def sync(
    conn,
    client: GoogleApiClient,
    client_id: UUID,
    connection: dict[str, Any],
) -> int:
    account_id, container_id = _account_and_container(connection)
    endpoint = (
        "https://tagmanager.googleapis.com/tagmanager/v2/"
        f"accounts/{account_id}/containers/{container_id}/versions:live"
    )
    live_version = client.request_json("GET", endpoint, SCOPE)
    findings = audit_tags(live_version.get("tag", []))
    return save_gtm_snapshot(
        conn,
        client_id,
        account_id,
        container_id,
        live_version,
        findings,
    )


def audit_tags(tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not any(tag.get("type") in {"googtag", "ga4_config"} for tag in tags):
        findings.append(
            _finding(
                "MISSING_GA4_CONFIG",
                "Google Tag / configuração do GA4 ausente",
                "Nenhuma Google Tag ou tag de configuração do GA4 foi encontrada no contêiner publicado.",
                "critical",
            )
        )
    if not any(tag.get("type") in {"gclidw", "conversion_linker"} for tag in tags):
        findings.append(
            _finding(
                "MISSING_CONVERSION_LINKER",
                "Conversion Linker ausente",
                "O contêiner não possui uma tag Conversion Linker publicada.",
                "high",
            )
        )

    orphan_tags = [tag.get("name", "Sem nome") for tag in tags if not tag.get("firingTriggerId")]
    if orphan_tags:
        findings.append(
            _finding(
                "ORPHAN_TAGS",
                "Tags órfãs detectadas",
                f"{len(orphan_tags)} tags publicadas não possuem gatilho associado.",
                "medium",
                {"tags": orphan_tags},
            )
        )

    custom_html_count = sum(1 for tag in tags if tag.get("type") == "html")
    if custom_html_count > 3:
        findings.append(
            _finding(
                "CUSTOM_HTML_EXCESS",
                "Excesso de tags HTML personalizadas",
                f"Foram encontradas {custom_html_count} tags HTML personalizadas.",
                "low",
                {"count": custom_html_count},
            )
        )

    if not findings:
        findings.append(
            _finding(
                "STATUS_HEALTHY",
                "Estrutura de rastreamento saudável",
                "Google Tag/GA4 e Conversion Linker foram localizados no contêiner publicado.",
                "info",
            )
        )
    return findings


def _account_and_container(connection: dict[str, Any]) -> tuple[str, str]:
    external_id = connection["external_account_id"]
    parent_id = connection.get("external_parent_id")
    if "/" in external_id:
        account_id, container_id = external_id.split("/", 1)
        return account_id, container_id
    if parent_id:
        return parent_id, external_id
    raise RuntimeError("Conexão GTM precisa de account/container ou external_parent_id.")


def _finding(
    code: str,
    title: str,
    description: str,
    severity: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "title": title,
        "description": description,
        "severity": severity,
        "metadata": metadata or {},
    }
