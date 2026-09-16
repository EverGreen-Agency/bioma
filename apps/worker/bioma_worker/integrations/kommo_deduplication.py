"""Motor Avançado de Deduplicação de Contatos e Reatribuição de Leads do Kommo CRM.

Preserva a relação 1:N entre Contato e Leads, normaliza telefones brasileiros (E.164,
tratando 8º e 9º dígitos e DDI 55), identifica clusters de duplicatas, elege o Contato Master,
reassocia todos os leads ao Master e fornece modo Simulação (Dry-Run) com relatório de auditoria.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

logger = logging.getLogger(__name__)


def normalize_brazilian_phone(raw_phone: str) -> Tuple[Optional[str], Optional[str]]:
    """Normaliza telefone brasileiro para E.164 canônico e gera chave de equivalência 8/9 dígitos.

    Retorna:
        (canonical_phone_e164, match_key) ou (None, None) se inválido.
    """
    if not raw_phone:
        return None, None

    digits = re.sub(r"\D", "", str(raw_phone))
    if not digits:
        return None, None

    # Remove zero inicial (ex: 011...)
    if digits.startswith("0") and len(digits) in (11, 12):
        digits = digits[1:]

    # Trata DDI 55
    if digits.startswith("55") and len(digits) in (12, 13):
        national = digits[2:]
    elif len(digits) in (10, 11):
        national = digits
    else:
        # Número internacional ou não-padrão BR
        if len(digits) >= 8:
            return f"+{digits}", digits
        return None, None

    ddd = national[:2]
    number = national[2:]

    # Validação básica de DDD brasileiro (11 a 99)
    if not (11 <= int(ddd) <= 99):
        return f"+55{national}", f"55{national}"

    # Trata equivalência entre 8 e 9 dígitos em celular brasileiro
    # Celulares BR começam com 6, 7, 8 ou 9
    if len(number) == 8:
        if number[0] in "6789":
            # Celular sem o 9 inicial -> chave canônica recebe o 9
            canonical = f"+55{ddd}9{number}"
            match_key = f"br_{ddd}_{number}"
            return canonical, match_key
        else:
            # Fixo (começa com 2, 3, 4, 5)
            canonical = f"+55{ddd}{number}"
            match_key = f"br_{ddd}_{number}"
            return canonical, match_key
    elif len(number) == 9:
        if number[0] == "9":
            canonical = f"+55{ddd}{number}"
            # match_key sem o 9 para parear com quem cadastrou sem 9
            match_key = f"br_{ddd}_{number[1:]}"
            return canonical, match_key
        else:
            canonical = f"+55{ddd}{number}"
            match_key = f"br_{ddd}_{number}"
            return canonical, match_key

    return f"+55{national}", f"55{national}"


def normalize_email(raw_email: str) -> Optional[str]:
    """Normaliza endereço de e-mail (lowercase, trim)."""
    if not raw_email or not isinstance(raw_email, str):
        return None
    cleaned = raw_email.strip().lower()
    if "@" in cleaned and "." in cleaned.split("@")[-1]:
        return cleaned
    return None


@dataclass
class DuplicateCluster:
    cluster_id: str
    match_reason: str  # ex: "phone:br_11_98765432" ou "email:dr.silva@exemplo.com"
    master_contact_id: int
    master_name: str
    duplicate_contacts: List[Dict[str, Any]]
    leads_to_reassign: List[int] = field(default_factory=list)
    fields_to_merge: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeduplicationReport:
    timestamp: str
    subdomain: str
    dry_run: bool
    total_contacts_scanned: int
    duplicate_clusters_count: int
    total_duplicates_detected: int
    total_leads_to_reassign: int
    clusters: List[DuplicateCluster] = field(default_factory=list)
    applied_changes: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KommoDeduplicationEngine:
    """Motor para ler contatos do Kommo, calcular clusters de duplicatas e executar merge seguro."""

    def __init__(self, subdomain: str, access_token: str):
        self.subdomain = subdomain
        self.access_token = access_token
        self.base_url = f"https://{subdomain}.kommo.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, client: httpx.AsyncClient, method: str, endpoint: str, **kwargs
    ) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = await client.request(method, url, headers=self.headers, **kwargs)
        if response.status_code == 204:
            return {}
        if response.status_code >= 400:
            logger.error("Erro na API do Kommo (%s %s): %s", response.status_code, url, response.text)
            response.raise_for_status()
        return response.json()

    async def fetch_all_contacts(
        self, client: httpx.AsyncClient, limit: int = 250
    ) -> List[Dict[str, Any]]:
        """Busca todos os contatos do Kommo com paginação e dados embutidos de leads."""
        contacts: List[Dict[str, Any]] = []
        page = 1
        logger.info("Iniciando busca de contatos no Kommo (subdomínio: %s)...", self.subdomain)

        while True:
            params = {"limit": limit, "page": page, "with": "leads"}
            data = await self._request(client, "GET", "/api/v4/contacts", params=params)
            if not data or "_embedded" not in data or "contacts" not in data["_embedded"]:
                break

            batch = data["_embedded"]["contacts"]
            contacts.extend(batch)
            logger.debug("Página %s: %s contatos carregados (total: %s)", page, len(batch), len(contacts))

            if len(batch) < limit:
                break
            page += 1

        logger.info("Total de contatos carregados: %s", len(contacts))
        return contacts

    def extract_contact_identifiers(
        self, contact: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Extrai telefones (chaves de match) e e-mails de um contato do Kommo."""
        phone_keys: List[str] = []
        emails: List[str] = []

        custom_fields = contact.get("custom_fields_values") or []
        for field_entry in custom_fields:
            code = (field_entry.get("field_code") or "").upper()
            values = field_entry.get("values") or []

            for val in values:
                raw_val = val.get("value")
                if not raw_val:
                    continue

                if code == "PHONE" or "PHONE" in code or "TELEFONE" in code:
                    _, match_key = normalize_brazilian_phone(str(raw_val))
                    if match_key:
                        phone_keys.append(match_key)
                elif code == "EMAIL" or "EMAIL" in code:
                    norm_email = normalize_email(str(raw_val))
                    if norm_email:
                        emails.append(norm_email)

        return phone_keys, emails

    def score_contact(self, contact: Dict[str, Any]) -> int:
        """Calcula score para eleger o Contato Master em um cluster."""
        score = 0

        # Leads vinculados (+20 pontos por lead)
        leads = (contact.get("_embedded") or {}).get("leads") or []
        score += len(leads) * 20

        # Nome completo com sobrenome (+10 pontos)
        name = (contact.get("name") or "").strip()
        if " " in name and len(name) >= 5:
            score += 10
        elif len(name) >= 3:
            score += 5

        # Campos customizados preenchidos (+2 pontos por campo)
        custom_fields = contact.get("custom_fields_values") or []
        score += len(custom_fields) * 2

        # Contato mais antigo (criação anterior) ganha desempate
        created_at = contact.get("created_at") or 0
        if created_at > 0:
            # Subtrai fração baseada no timestamp para preferir o mais antigo em empate
            score += max(0, 1000 - int(created_at / 1_000_000))

        return score

    def build_clusters(self, contacts: List[Dict[str, Any]]) -> List[DuplicateCluster]:
        """Agrupa contatos com base em telefones equivalentes e e-mails."""
        phone_to_contacts: Dict[str, List[Dict[str, Any]]] = {}
        email_to_contacts: Dict[str, List[Dict[str, Any]]] = {}

        for contact in contacts:
            phone_keys, emails = self.extract_contact_identifiers(contact)
            for pkey in phone_keys:
                phone_to_contacts.setdefault(pkey, []).append(contact)
            for em in emails:
                email_to_contacts.setdefault(em, []).append(contact)

        # Usar Union-Find para mesclar grupos de contatos que compartilham telefone ou e-mail
        parent: Dict[int, int] = {}

        def find(item: int) -> int:
            if parent.setdefault(item, item) != item:
                parent[item] = find(parent[item])
            return parent[item]

        def union(item1: int, item2: int):
            root1 = find(item1)
            root2 = find(item2)
            if root1 != root2:
                parent[root2] = root1

        contact_map: Dict[int, Dict[str, Any]] = {}
        reason_map: Dict[int, str] = {}

        for contact in contacts:
            cid = contact["id"]
            contact_map[cid] = contact

        # Unifica por telefone
        for pkey, matched_list in phone_to_contacts.items():
            if len(matched_list) > 1:
                first_id = matched_list[0]["id"]
                for other in matched_list[1:]:
                    union(first_id, other["id"])
                    reason_map[other["id"]] = f"Telefone correspondente ({pkey})"

        # Unifica por e-mail
        for em, matched_list in email_to_contacts.items():
            if len(matched_list) > 1:
                first_id = matched_list[0]["id"]
                for other in matched_list[1:]:
                    union(first_id, other["id"])
                    if other["id"] not in reason_map:
                        reason_map[other["id"]] = f"E-mail correspondente ({em})"

        # Agrupa os clusters formados
        raw_clusters: Dict[int, List[Dict[str, Any]]] = {}
        for cid in contact_map:
            root = find(cid)
            raw_clusters.setdefault(root, []).append(contact_map[cid])

        clusters: List[DuplicateCluster] = []
        cluster_idx = 1

        for root, members in raw_clusters.items():
            if len(members) <= 1:
                continue

            # Eleger o Master com maior score
            sorted_members = sorted(members, key=self.score_contact, reverse=True)
            master = sorted_members[0]
            duplicates = sorted_members[1:]

            # Coleta todos os leads dos duplicados para reatribuir ao Master
            master_lead_ids = {
                l["id"] for l in ((master.get("_embedded") or {}).get("leads") or [])
            }
            leads_to_reassign: List[int] = []

            for dup in duplicates:
                dup_leads = (dup.get("_embedded") or {}).get("leads") or []
                for lead in dup_leads:
                    lid = lead["id"]
                    if lid not in master_lead_ids:
                        leads_to_reassign.append(lid)

            match_reason = reason_map.get(duplicates[0]["id"], "Identificador compartilhado")

            clusters.append(
                DuplicateCluster(
                    cluster_id=f"cluster_{cluster_idx}",
                    match_reason=match_reason,
                    master_contact_id=master["id"],
                    master_name=master.get("name") or "Sem nome",
                    duplicate_contacts=[
                        {
                            "id": d["id"],
                            "name": d.get("name"),
                            "created_at": d.get("created_at"),
                            "leads_count": len((d.get("_embedded") or {}).get("leads") or []),
                        }
                        for d in duplicates
                    ],
                    leads_to_reassign=leads_to_reassign,
                )
            )
            cluster_idx += 1

        return clusters

    async def run_simulation(
        self, contacts: Optional[List[Dict[str, Any]]] = None
    ) -> DeduplicationReport:
        """Executa simulação completa (Dry-Run) sem modificar nada no Kommo."""
        async with httpx.AsyncClient() as client:
            if contacts is None:
                contacts = await self.fetch_all_contacts(client)

        clusters = self.build_clusters(contacts)
        total_dups = sum(len(c.duplicate_contacts) for c in clusters)
        total_leads_reassigned = sum(len(c.leads_to_reassign) for c in clusters)

        report = DeduplicationReport(
            timestamp=datetime.now().isoformat(),
            subdomain=self.subdomain,
            dry_run=True,
            total_contacts_scanned=len(contacts),
            duplicate_clusters_count=len(clusters),
            total_duplicates_detected=total_dups,
            total_leads_to_reassign=total_leads_reassigned,
            clusters=clusters,
        )
        return report

    async def apply_deduplication(
        self,
        report: DeduplicationReport,
        safe_mode_tag: str = "[DUPLICADO_UNIFICADO]",
        delete_duplicates: bool = False,
    ) -> Dict[str, Any]:
        """Aplica a unificação aprovada: reatribui leads, insere nota e etiqueta/remove duplicatas."""
        logger.info(
            "Iniciando aplicação de deduplicação (%s clusters, delete=%s)...",
            len(report.clusters),
            delete_duplicates,
        )
        stats = {
            "leads_reassigned": 0,
            "contacts_tagged": 0,
            "contacts_deleted": 0,
            "errors": [],
        }

        async with httpx.AsyncClient() as client:
            for cluster in report.clusters:
                master_id = cluster.master_contact_id

                # 1. Reatribuir leads dos duplicados para o Master
                for lead_id in cluster.leads_to_reassign:
                    try:
                        patch_payload = {
                            "_embedded": {
                                "contacts": [{"id": master_id}]
                            }
                        }
                        await self._request(
                            client, "PATCH", f"/api/v4/leads/{lead_id}", json=patch_payload
                        )
                        stats["leads_reassigned"] += 1
                    except Exception as e:
                        logger.error("Erro ao reatribuir lead %s para master %s: %s", lead_id, master_id, e)
                        stats["errors"].append(f"Lead {lead_id}: {str(e)}")

                # 2. Registrar nota de auditoria no Master
                dup_ids = [str(d["id"]) for d in cluster.duplicate_contacts]
                note_text = (
                    f"Bioma Dedup: Contatos duplicados mesclados: {', '.join(dup_ids)}. "
                    f"Leads reatribuídos: {cluster.leads_to_reassign or 'Nenhum'}."
                )
                try:
                    await self._request(
                        client,
                        "POST",
                        f"/api/v4/contacts/{master_id}/notes",
                        json=[{"note_type": "common", "params": {"text": note_text}}],
                    )
                except Exception as e:
                    logger.warning("Não foi possível criar nota no master %s: %s", master_id, e)

                # 3. Tratar duplicatas (etiquetar ou deletar)
                for dup in cluster.duplicate_contacts:
                    dup_id = dup["id"]
                    try:
                        if delete_duplicates:
                            await self._request(client, "DELETE", f"/api/v4/contacts/{dup_id}")
                            stats["contacts_deleted"] += 1
                        else:
                            # Safe mode: adiciona tag e renomeia
                            patch_dup = {
                                "name": f"{dup.get('name') or 'Contato'} {safe_mode_tag}"
                            }
                            await self._request(
                                client, "PATCH", f"/api/v4/contacts/{dup_id}", json=patch_dup
                            )
                            stats["contacts_tagged"] += 1
                    except Exception as e:
                        logger.error("Erro ao processar duplicata %s: %s", dup_id, e)
                        stats["errors"].append(f"Contato {dup_id}: {str(e)}")

        report.dry_run = False
        report.applied_changes = stats
        return stats
