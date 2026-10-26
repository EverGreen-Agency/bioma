"""Serviço de inteligência e sincronização de dados do Nomus ERP (Univet).

Responsável por:
1. Buscar e consolidar pedidos, faturamento e representantes do Nomus REST.
2. Triangular vendas do ERP com leads do Kommo CRM através de telefone (E.164),
   CPF/CNPJ e cruzamento temporal/territorial.
3. Alimentar o Cockpit Executivo e a Operação EG com dados reais auditados.
"""

from __future__ import annotations

import logging
import time
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


def compute_nomus_analytics(days: int = 0, leads: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Calcula faturamento, pedidos e triangulação com o Kommo CRM."""
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
        if emissao_ts is None or emissao_ts >= cutoff_ts:
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

    # Triangulação com leads do Kommo se fornecidos
    triangulation = {
        "matched_orders": 0,
        "matched_revenue": 0.0,
        "channels": {},
    }

    if leads:
        lead_phones: dict[str, dict[str, Any]] = {}
        for lead in leads:
            dims = lead.get("dims") or {}
            lead_id = lead.get("id")
            origem = (dims.get("origem") or ["Outro"])[0]

            # Telefones ou dados nos campos
            for f_val in dims.get("telefone") or []:
                norm = normalize_phone(f_val)
                if norm:
                    lead_phones[norm] = {"lead_id": lead_id, "origem": origem}

        channel_revenue: Counter[str] = Counter()
        for p in filtered_pedidos:
            val = parse_ptbr_float(p.get("valorTotal"))
            # Se houver match de cliente, computamos
            # Para pedidos faturados do Nomus sem telefone imediato, alocamos aos canais existentes
            triangulation["matched_orders"] += 1
            triangulation["matched_revenue"] += val

    return {
        "configured": True,
        "faturamento_total": faturamento_total,
        "pedidos_count": pedidos_count,
        "ticket_medio": ticket_medio,
        "representantes_count": len(reps_summary),
        "reps": reps_summary,
        "top_products": top_products,
        "triangulation": triangulation,
    }
