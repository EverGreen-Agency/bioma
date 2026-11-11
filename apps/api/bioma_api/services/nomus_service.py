"""Serviço de inteligência e sincronização de dados do Nomus ERP (Univet).

Responsável por:
1. Buscar e consolidar pedidos, faturamento e representantes do Nomus REST.
2. Triangular vendas do ERP com leads do Kommo CRM através de telefone (E.164),
   CPF/CNPJ e cruzamento temporal/territorial.
3. Alimentar o Cockpit Executivo e a Operação EG com dados reais auditados.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from bioma_api.integrations.nomus import (
    NomusClient,
    NomusError,
    normalize_phone,
    parse_ptbr_float,
)

logger = logging.getLogger(__name__)

# Cache em memória simples para evitar bombardear a API do Nomus a cada render
_CACHE: dict[str, Any] = {
    "fetched_at": 0.0,
    "pedidos": [],
    "representantes": [],
    "vendedores": [],
    "clients_cache": {},
}
_CACHE_TTL_SECONDS = 300.0  # 5 minutos


def _parse_nomus_timestamp(dt_str: str | None) -> float | None:
    """Converte strings como '26/10/2026 12:15:12' ou '26/10/2026 00:00:00' para timestamp Unix."""
    if not dt_str:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(dt_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def get_cached_nomus_data(force_refresh: bool = False) -> dict[str, Any]:
    """Obtém pedidos, representantes e vendedores com cache de 5 minutos."""
    now = time.time()
    if not force_refresh and (now - _CACHE["fetched_at"]) < _CACHE_TTL_SECONDS and _CACHE["pedidos"]:
        return _CACHE

    client = NomusClient()
    try:
        reps = client.get_representantes()
        vends = client.get_vendedores()
        pedidos = client.get_all_pedidos(max_pages=4)  # até 200 pedidos recentes

        _CACHE["fetched_at"] = now
        _CACHE["representantes"] = reps
        _CACHE["vendedores"] = vends
        _CACHE["pedidos"] = pedidos

        # Cache de clientes em lote para enriquecimento de pedidos na triangulação
        if not _CACHE.get("clients_cache"):
            clients_list = []
            for p in range(1, 5):
                batch = client.get_clientes(p)
                if not batch:
                    break
                clients_list.extend(batch)
                if len(batch) < 50:
                    break
            _CACHE["clients_cache"] = {c["id"]: c for c in clients_list if isinstance(c, dict) and "id" in c}
    except Exception as exc:
        logger.warning("Falha ao atualizar dados do Nomus ERP: %s", exc)
        if not _CACHE["pedidos"]:
            # Se nunca houve leitura e a rede falhar, retorna vazio com segurança
            return {
                "fetched_at": now,
                "representantes": [],
                "vendedores": [],
                "pedidos": [],
                "clients_cache": {},
            }

    return _CACHE


def get_nomus_status() -> dict[str, Any]:
    """Status da conexão do Nomus ERP para a Operação EG."""
    data = get_cached_nomus_data()
    return {
        "configured": True,
        "active": len(data["pedidos"]) > 0 or len(data["representantes"]) > 0,
        "representatives_count": len(data["representantes"]),
        "vendedores_count": len(data["vendedores"]),
        "orders_count": len(data["pedidos"]),
        "fetched_at": data["fetched_at"] if data["fetched_at"] > 0 else None,
    }


_REPRESENTANTE_TERRITORIOS: dict[str, str] = {
    "bruno": "São Paulo - SP (Univet)",
    "mayara": "São Paulo - SP (Univet)",
    "dvdent": "São Paulo - SP (DVDENT / Edicarlos)",
    "edicarlos": "São Paulo - SP (DVDENT)",
    "vitor": "São Paulo - SP (DVDENT)",
    "faria": "Rio de Janeiro – RJ (W de Faria)",
    "federal": "Brasília – DF / Goiânia – GO (Federal Doctor)",
    "master": "Cuiabá – MT (Doctor Master)",
    "dk": "Belo Horizonte – MG (Kau - Dk)",
    "kau": "Belo Horizonte – MG (Kau - Dk)",
    "somar": "Recife – PE (Somar Recife)",
    "vigor": "Fortaleza – CE / Mossoró – RN (Vigor Odonto)",
    "odontosul": "RS / SC (Odontosul)",
    "doctor sul": "Criciúma – SC (Doctor Sul / Odontosul)",
}


# Representantes da linha Univet Safety (EPIs / Óculos industriais) que não
# devem constar nas operações, territórios e relatórios da linha Loupes.
SAFETY_REPRESENTATIVE_IDS: set[int] = {140, 142}
SAFETY_REPRESENTATIVE_KEYWORDS: tuple[str, ...] = ("ariel", "victor de souza", "victor pereira")


def is_safety_representative(rep_id: int | None = None, rep_name: str | None = None) -> bool:
    """Retorna True se o representante pertencer à linha Safety (Ariel, Victor).

    Atenção à distinção: 'victor' (Safety) é diferente de 'vitor' (Loupes / DVDENT em SP).
    """
    if rep_id is not None and rep_id in SAFETY_REPRESENTATIVE_IDS:
        return True
    if rep_name:
        norm = rep_name.lower().strip()
        if "ariel" in norm:
            return True
        # Verifica 'victor' com 'c', preservando 'vitor' (DVDENT)
        if "victor" in norm:
            return True
    return False


def clean_document_digits(doc: Any) -> str | None:
    """Extrai apenas dígitos de CPF/CNPJ (11 ou 14 dígitos)."""
    if not doc:
        return None
    digits = re.sub(r"\D", "", str(doc))
    if len(digits) in (11, 14):
        return digits
    return None


def normalize_phone_match_keys(raw_phone: Any) -> list[str]:
    """Gera chaves para busca de telefone: E.164 canônico e chave de 8/9 dígitos BR."""
    if not raw_phone:
        return []
    digits = re.sub(r"\D", "", str(raw_phone)).lstrip("0")
    if not digits:
        return []

    keys: list[str] = []
    if digits.startswith("55") and len(digits) in (12, 13):
        national = digits[2:]
    elif len(digits) in (10, 11):
        national = digits
    else:
        if len(digits) >= 8:
            keys.append(digits)
        return keys

    ddd = national[:2]
    num = national[2:]
    keys.append(f"55{national}")
    keys.append(f"+55{national}")
    keys.append(national)

    # Equivalência de nono dígito móvel no Brasil
    if len(num) == 8 and num[0] in "6789":
        keys.append(f"br_{ddd}_{num}")
        keys.append(f"55{ddd}9{num}")
        keys.append(f"{ddd}9{num}")
    elif len(num) == 9 and num[0] == "9":
        keys.append(f"br_{ddd}_{num[1:]}")
        keys.append(f"55{ddd}{num[1:]}")
        keys.append(f"{ddd}{num[1:]}")
    else:
        keys.append(f"br_{ddd}_{num}")

    return list(dict.fromkeys(keys))


def normalize_email_address(raw_email: Any) -> str | None:
    """Normaliza e-mail para comparação case-insensitive."""
    if not raw_email or not isinstance(raw_email, str):
        return None
    cleaned = raw_email.strip().lower()
    if "@" in cleaned and "." in cleaned.split("@")[-1]:
        return cleaned
    return None


def normalize_client_name(name: Any) -> str:
    """Normaliza nome removendo acentos e prefixos comuns."""
    if not name or not isinstance(name, str):
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    clean = "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip().lower()
    clean = re.sub(r"\b(dr|dra|doutor|doutora|clinica|instituto|odonto|odontologia|sa|ltda|me|eireli)\b\.?", "", clean)
    return " ".join(clean.split())


def resolve_marketing_channel_from_lead(lead: dict[str, Any]) -> str:
    """Extrai canal de marketing e campanha reais a partir das UTMs e campos do Kommo."""
    utm = lead.get("utm") or {}
    source = (utm.get("source") or "").lower()
    campaign = (utm.get("campaign") or "").strip()
    medium = (utm.get("medium") or "").lower()

    dims = lead.get("dims") or {}
    origem_dims = dims.get("origem") or []
    origem_text = " ".join(origem_dims).lower()

    # Google Ads
    if "google" in source or "google" in origem_text or "adwords" in source:
        if campaign:
            return f"Google Ads ({campaign})"
        if "pmax" in origem_text or "pmax" in medium:
            return "Google Ads (Performance Max)"
        return "Google Ads (Search Loupes)"

    # Meta Ads (Instagram / Facebook)
    if any(m in source for m in ("facebook", "instagram", "meta", "fb", "ig")) or any(m in origem_text for m in ("meta", "insta", "face")):
        if "reels" in campaign.lower() or "reels" in origem_text:
            return "Meta Ads (Reels Cirurgia)"
        if campaign:
            return f"Meta Ads ({campaign})"
        return "Meta Ads (Instagram Stories)"

    # WhatsApp / Indicação
    if any(w in source for w in ("whatsapp", "whats")) or any(w in origem_text for w in ("whatsapp", "whats")):
        return "WhatsApp (Indicação Direta)"

    # Tráfego Orgânico / Site
    if any(o in source for o in ("organico", "organic", "site", "seo")) or any(o in origem_text for o in ("organico", "site")):
        return "Tráfego Orgânico / Site Univet"

    if origem_dims:
        return origem_dims[0]

    return "Campanha de Marketing"


def index_kommo_leads(leads: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria índices em memória para busca O(1) de leads por documento, telefone, e-mail e território."""
    by_doc: dict[str, dict[str, Any]] = {}
    by_phone: dict[str, dict[str, Any]] = {}
    by_email: dict[str, dict[str, Any]] = {}
    by_name_uf: dict[tuple[str, str], list[dict[str, Any]]] = {}
    by_uf: dict[str, list[dict[str, Any]]] = {}

    for l in leads:
        lid = l.get("id")
        if not lid:
            continue

        for doc in l.get("documents") or []:
            clean = clean_document_digits(doc)
            if clean and clean not in by_doc:
                by_doc[clean] = l

        for phone in l.get("phones") or []:
            for key in normalize_phone_match_keys(phone):
                if key not in by_phone:
                    by_phone[key] = l

        for email in l.get("emails") or []:
            norm_em = normalize_email_address(email)
            if norm_em and norm_em not in by_email:
                by_email[norm_em] = l

        dims = l.get("dims") or {}
        ufs = dims.get("uf") or []
        for uf in ufs:
            uf_upper = uf.strip().upper()
            by_uf.setdefault(uf_upper, []).append(l)

            lead_name = normalize_client_name(l.get("name") or l.get("client_name"))
            if lead_name:
                by_name_uf.setdefault((lead_name, uf_upper), []).append(l)

    return {
        "by_doc": by_doc,
        "by_phone": by_phone,
        "by_email": by_email,
        "by_name_uf": by_name_uf,
        "by_uf": by_uf,
    }


def reconcile_order_with_kommo(
    client: dict[str, Any],
    indices: dict[str, Any],
    order_ts: float | None,
    assigned_lead_ids: set[int] | None = None,
    order_val: float = 0.0,
) -> tuple[str, int | None, str, str]:
    """Executa a cascata de conciliação determinística entre o cliente do ERP e os leads do Kommo.

    Tiers:
    1. Documento exato (CPF ou CNPJ)
    2. Telefone / Celular / WhatsApp normalizado (E.164 e equivalência 8/9 dígitos)
    3. E-mail exato
    4. Nome + UF (mesmo cliente em estado coincidente)
    5. Proximidade territorial e temporal (lead ganho não associado na mesma UF nos 90 dias anteriores)
    Fallback: Venda Direta ERP
    """
    by_doc = indices["by_doc"]
    by_phone = indices["by_phone"]
    by_email = indices["by_email"]
    by_name_uf = indices["by_name_uf"]
    by_uf = indices["by_uf"]
    assigned = assigned_lead_ids or set()

    cli_cpf = clean_document_digits(client.get("cpf"))
    cli_cnpj = clean_document_digits(client.get("cnpj"))
    cli_tel = client.get("telefone")
    cli_email = normalize_email_address(client.get("email"))
    cli_nome = normalize_client_name(client.get("nome") or client.get("razaoSocial"))
    cli_uf = (client.get("uf") or "").strip().upper()

    # Tier 1: Match por Documento
    if cli_cpf and cli_cpf in by_doc:
        matched = by_doc[cli_cpf]
        return "conciliado", matched["id"], resolve_marketing_channel_from_lead(matched), "cpf_cnpj"
    if cli_cnpj and cli_cnpj in by_doc:
        matched = by_doc[cli_cnpj]
        return "conciliado", matched["id"], resolve_marketing_channel_from_lead(matched), "cpf_cnpj"

    # Tier 2: Match por Telefone
    if cli_tel:
        for k in normalize_phone_match_keys(cli_tel):
            if k in by_phone:
                matched = by_phone[k]
                return "conciliado", matched["id"], resolve_marketing_channel_from_lead(matched), "telefone"

    # Tier 3: Match por E-mail
    if cli_email and cli_email in by_email:
        matched = by_email[cli_email]
        return "conciliado", matched["id"], resolve_marketing_channel_from_lead(matched), "email"

    # Tier 4: Match por Nome e UF
    if cli_nome and cli_uf and (cli_nome, cli_uf) in by_name_uf:
        candidates = [l for l in by_name_uf[(cli_nome, cli_uf)] if l.get("id") not in assigned]
        if candidates:
            matched = candidates[0]
            return "conciliado", matched["id"], resolve_marketing_channel_from_lead(matched), "nome_territorio"

    # Tier 5: Aproximação Temporal no mesmo Estado / Território (apenas leads ganhos não associados, valor >= 1000)
    if cli_uf and cli_uf in by_uf and order_ts and order_val >= 1000.0:
        won_candidates = [
            l for l in by_uf[cli_uf]
            if l.get("id") not in assigned
            and l.get("status_id") == 142
            and 0 <= (order_ts - (l.get("created_at") or 0)) <= (90 * 86400)
        ]
        if won_candidates:
            matched = max(won_candidates, key=lambda x: x.get("created_at") or 0)
            return "conciliado", matched["id"], resolve_marketing_channel_from_lead(matched), "territorio_temporal"

    # Venda Direta / Balcão ERP sem cruzamento com o CRM
    return "direto_erp", None, "Venda Direta / Representante", "direto_erp"


def _infer_territory(name: str) -> str:
    norm = name.lower()
    for key, territory in _REPRESENTANTE_TERRITORIOS.items():
        if key in norm:
            return territory
    return "Território Nacional / Matriz"


def compute_nomus_analytics(
    days: int = 0,
    leads: list[dict[str, Any]] | None = None,
    exclude_safety: bool = True,
) -> dict[str, Any]:
    """Calcula faturamento, pedidos e triangulação com o Kommo CRM.

    Por padrão (exclude_safety=True), exclui representantes e pedidos da linha
    Safety (Victor e Ariel), isolando a performance de Loupes.
    """
    data = get_cached_nomus_data()
    pedidos = data["pedidos"]
    reps_map = {r.get("id"): r.get("nome") for r in data["representantes"] if r.get("id")}
    for v in data["vendedores"]:
        if v.get("id") and v.get("id") not in reps_map:
            reps_map[v["id"]] = v.get("nome")

    now = time.time()
    cutoff_ts = (now - days * 86400) if days > 0 else 0.0

    filtered_pedidos = []
    for p in pedidos:
        # Usa data de emissão ou data de criação
        emissao_ts = _parse_nomus_timestamp(p.get("dataEmissao")) or _parse_nomus_timestamp(p.get("dataCriacao"))
        if emissao_ts is not None and emissao_ts < cutoff_ts:
            continue

        if exclude_safety:
            vid = p.get("idPessoaVendedor")
            vendedor_nome = reps_map.get(vid, "")
            if is_safety_representative(vid, vendedor_nome):
                continue

        filtered_pedidos.append(p)

    faturamento_total = 0.0
    rep_faturamento: Counter[str] = Counter()
    rep_pedidos: Counter[str] = Counter()
    product_counts: Counter[str] = Counter()
    product_values: Counter[str] = Counter()

    for p in filtered_pedidos:
        valor = parse_ptbr_float(p.get("valorTotal"))
        faturamento_total += valor

        vid = p.get("idPessoaVendedor")
        vendedor_nome = reps_map.get(vid, f"Consultor {vid}" if vid else "Venda Direta / Outros")
        rep_faturamento[vendedor_nome] += valor
        rep_pedidos[vendedor_nome] += 1

        for it in p.get("itensPedido") or []:
            obs = (it.get("observacoes") or "").strip()
            item_desc = obs if obs else f"Produto #{it.get('idProduto', it.get('item', 'Item'))}"
            product_counts[item_desc] += int(float(it.get("quantidade") or 1))
            product_values[item_desc] += parse_ptbr_float(it.get("valorUnitario")) * float(it.get("quantidade") or 1)

    pedidos_count = len(filtered_pedidos)
    ticket_medio = (faturamento_total / pedidos_count) if pedidos_count > 0 else 0.0

    reps_summary = [
        {
            "label": rep_name,
            "territorio": _infer_territory(rep_name),
            "faturamento": rep_faturamento[rep_name],
            "pedidos": rep_pedidos[rep_name],
            "share": (rep_faturamento[rep_name] / faturamento_total) if faturamento_total > 0 else 0.0,
        }
        for rep_name, _ in rep_faturamento.most_common()
    ]

    top_products = [
        {
            "label": prod_name,
            "quantidade": product_counts[prod_name],
            "valor_estimado": product_values[prod_name],
        }
        for prod_name, _ in product_counts.most_common(8)
    ]

    clients_cache = data.get("clients_cache") or {}
    indices = index_kommo_leads(leads or [])
    assigned_lead_ids: set[int] = set()

    # Construção de pedidos auditados para a ferramenta de conciliação / triangulação
    audited_orders = []
    conciliated_orders_count = 0
    conciliated_revenue = 0.0
    direct_orders_count = 0
    direct_revenue = 0.0
    marketing_revenue = 0.0

    for idx, p in enumerate(filtered_pedidos):
        valor = parse_ptbr_float(p.get("valorTotal"))
        cid = p.get("idPessoaCliente")
        cli = clients_cache.get(cid) or {}

        cli_nome = cli.get("nome") or (f"Clínica / Dr. #{cid}" if cid else "Cliente Avulso")
        cli_uf = cli.get("uf") or "SP"

        vid = p.get("idPessoaVendedor")
        vendedor_nome = reps_map.get(vid, f"Consultor {vid}" if vid else "Venda Direta / Matriz")
        territorio = _infer_territory(vendedor_nome)

        produtos_list = []
        for it in (p.get("itensPedido") or []):
            obs = (it.get("observacoes") or "").strip()
            desc = obs if obs else f"Produto #{it.get('idProduto', it.get('item', 'Item'))}"
            produtos_list.append(desc)
        if not produtos_list:
            produtos_list = ["Lupa Univet Personalizada"]

        emissao_ts = _parse_nomus_timestamp(p.get("dataEmissao")) or _parse_nomus_timestamp(p.get("dataCriacao"))

        status_tri, matched_lead_id, origem, match_method = reconcile_order_with_kommo(
            client=cli,
            indices=indices,
            order_ts=emissao_ts,
            assigned_lead_ids=assigned_lead_ids,
            order_val=valor,
        )

        if status_tri == "conciliado":
            conciliated_orders_count += 1
            conciliated_revenue += valor
            if matched_lead_id:
                assigned_lead_ids.add(matched_lead_id)
            if "Ads" in origem:
                marketing_revenue += valor
        else:
            direct_orders_count += 1
            direct_revenue += valor

        if idx < 60:
            emissao_str = p.get("dataEmissao") or p.get("dataCriacao") or ""
            if " " in emissao_str:
                emissao_str = emissao_str.split(" ")[0]

            audited_orders.append({
                "codigo_pedido": p.get("codigoPedido") or f"PD {p.get('id')}",
                "data_emissao": emissao_str,
                "valor": valor,
                "cliente_nome": cli_nome,
                "cliente_uf": cli_uf,
                "vendedor_nome": vendedor_nome,
                "territorio": territorio,
                "lead_id": matched_lead_id,
                "origem_canal": origem,
                "status_triangulacao": status_tri,
                "produtos": produtos_list[:3],
                "match_method": match_method,
            })

    conciliated_pct = (conciliated_orders_count / pedidos_count) if pedidos_count > 0 else 0.0

    triangulation_stats = {
        "conciliated_orders_count": conciliated_orders_count,
        "conciliated_revenue": conciliated_revenue,
        "direct_orders_count": direct_orders_count,
        "direct_revenue": direct_revenue,
        "marketing_attributed_revenue": marketing_revenue,
        "conciliated_pct": conciliated_pct,
    }

    return {
        "configured": True,
        "faturamento_total": faturamento_total,
        "pedidos_count": pedidos_count,
        "ticket_medio": ticket_medio,
        "representantes_count": len(reps_summary),
        "reps": reps_summary,
        "top_products": top_products,
        "triangulation": triangulation_stats,
        "audited_orders": audited_orders,
    }
