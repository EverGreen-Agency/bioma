"""Detectores de vitória: o que o banco já sabe e ninguém estava lendo.

Cada detector é uma consulta que devolve vitórias candidatas desde a última
varredura. Regras que valem para todos:

1. **Idempotência por `dedupe_key`.** Rodar de hora em hora não pode transformar
   a mesma proposta ganha em 24 vitórias no mural.
2. **Evidência obrigatória.** Toda vitória automática carrega a tabela, o id e o
   que estava lá. Sem isso ela é indistinguível de vitória inventada — e o mural
   inteiro perde o valor no dia em que alguém duvidar de uma linha.
3. **Janela desde a última varredura.** Sem isso, a primeira execução despejaria
   a história inteira de uma vez, enterrando o que aconteceu hoje.
4. **Nada de heurística de "parece uma vitória".** Se o dado não diz, não vira
   vitória. É melhor um mural com menos linhas do que um mural que comemora o
   que não aconteceu.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

# Assinatura: (conn, desde) -> lista de vitórias candidatas.
Detector = Callable[[Any, datetime], list[dict[str, Any]]]


def _win(
    rule_key: str,
    dedupe_id: Any,
    title: str,
    description: str | None,
    category: str,
    occurred_at: datetime | None,
    evidence: dict,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "rule_key": rule_key,
        "dedupe_key": f"{rule_key}:{dedupe_id}",
        "title": title[:200],
        "description": description,
        "category": category,
        "source": "automatic",
        "occurred_at": occurred_at or datetime.now(timezone.utc),
        "evidence": evidence,
        **extra,
    }


def proposta_ganha(conn, since: datetime) -> list[dict[str, Any]]:
    """Proposta que virou 'won'. A vitória comercial mais direta que existe."""
    rows = conn.execute(
        """
        select id, client_name, title, pricing_cents, updated_at
        from commercial_proposals
        where status = 'won' and updated_at >= %s
        order by updated_at
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "proposta_ganha",
            row["id"],
            f"Proposta ganha: {row['client_name']}",
            row["title"],
            "comercial",
            row["updated_at"],
            {"table": "commercial_proposals", "id": str(row["id"]), "status": "won"},
            metric_value=(row["pricing_cents"] or 0) / 100 or None,
            metric_unit="R$" if row["pricing_cents"] else None,
            is_ceo=True,
        )
        for row in rows
    ]


def cliente_ativado(conn, since: datetime) -> list[dict[str, Any]]:
    """Cliente que passou a ativo. Conta como vitória uma vez, na virada."""
    rows = conn.execute(
        """
        select id, name, organization_id, updated_at
        from clients
        where status = 'active' and updated_at >= %s
        order by updated_at
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "cliente_ativado",
            row["id"],
            f"Cliente ativo na carteira: {row['name']}",
            None,
            "comercial",
            row["updated_at"],
            {"table": "clients", "id": str(row["id"]), "status": "active"},
            is_ceo=True,
        )
        for row in rows
    ]


def entrega_aceita(conn, since: datetime) -> list[dict[str, Any]]:
    """Entrega ACEITA pelo cliente — não apenas concluída pela EG.

    A distinção é o ponto: entrega concluída é trabalho feito; entrega aceita é
    trabalho reconhecido. Só a segunda é vitória.
    """
    rows = conn.execute(
        """
        select d.id, d.title, d.completed_at, d.organization_id, o.name as client_name,
               w.id as workspace_id
        from deliverables d
        join organizations o on o.id = d.organization_id
        left join workspaces w on w.subject_organization_id = d.organization_id and w.kind = 'client'
        where d.status = 'accepted' and d.completed_at >= %s
        order by d.completed_at
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "entrega_aceita",
            row["id"],
            f"Entrega aceita: {row['title']}",
            f"Cliente: {row['client_name']}",
            "cliente",
            row["completed_at"],
            {"table": "deliverables", "id": str(row["id"]), "status": "accepted"},
            workspace_id=row["workspace_id"],
        )
        for row in rows
    ]


def projeto_concluido(conn, since: datetime) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select id, name, workspace_id, updated_at
        from projects
        where status = 'completed' and updated_at >= %s
        order by updated_at
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "projeto_concluido",
            row["id"],
            f"Projeto concluído: {row['name']}",
            None,
            "operacao",
            row["updated_at"],
            {"table": "projects", "id": str(row["id"]), "status": "completed"},
            workspace_id=row["workspace_id"],
            is_ceo=True,
        )
        for row in rows
    ]


def prospect_aprovado(conn, since: datetime) -> list[dict[str, Any]]:
    """Prospect do Radar Local aprovado para abordagem."""
    rows = conn.execute(
        """
        select id, name, reviewed_at
        from local_radar_prospects
        where review_status = 'approved' and reviewed_at >= %s
        order by reviewed_at
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "prospect_aprovado",
            row["id"],
            f"Prospect aprovado para abordagem: {row['name']}",
            None,
            "comercial",
            row["reviewed_at"],
            {"table": "local_radar_prospects", "id": str(row["id"])},
        )
        for row in rows
    ]


def pico_de_propostas(conn, since: datetime) -> list[dict[str, Any]]:
    """Dia com mais propostas enviadas que a média das 4 semanas anteriores.

    "Pico" precisa de linha de base — sem ela, "3 propostas hoje" não diz nada.
    Compara o dia contra a média diária do mês anterior e só dispara quando
    passa do dobro E com pelo menos 3, porque de 1 para 2 não é pico, é acaso.

    A dedupe é por DIA: um dia tem no máximo um pico.
    """
    rows = conn.execute(
        """
        with diario as (
          select date_trunc('day', created_at) as dia, count(*) as total
          from commercial_proposals
          where created_at >= now() - interval '35 days'
          group by 1
        ),
        base as (
          select coalesce(avg(total), 0) as media
          from diario
          where dia < date_trunc('day', now())
        )
        select d.dia, d.total, b.media
        from diario d, base b
        where d.dia >= %s
          and d.total >= 3
          and d.total > b.media * 2
        order by d.dia
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "pico_de_propostas",
            row["dia"].date().isoformat(),
            f"Pico de propostas: {row['total']} em um dia",
            f"A média diária das últimas semanas era {float(row['media']):.1f}.",
            "comercial",
            row["dia"],
            {
                "table": "commercial_proposals",
                "aggregate": "count por dia",
                "day": row["dia"].date().isoformat(),
                "total": row["total"],
                "baseline_avg": float(row["media"]),
            },
            metric_value=row["total"],
            metric_unit="propostas",
        )
        for row in rows
    ]


def integracao_conectada(conn, since: datetime) -> list[dict[str, Any]]:
    """Primeira conexão de dados de um cliente — o cliente saiu do escuro."""
    rows = conn.execute(
        """
        select pc.id, pc.provider, pc.workspace_id, pc.updated_at, w.name as workspace_name
        from performance_connections pc
        join workspaces w on w.id = pc.workspace_id
        where pc.status = 'connected' and pc.updated_at >= %s
        order by pc.updated_at
        """,
        (since,),
    ).fetchall()
    return [
        _win(
            "integracao_conectada",
            row["id"],
            f"Integração conectada: {row['provider']} · {row['workspace_name']}",
            "Os dados desse canal passam a alimentar o hub do cliente.",
            "operacao",
            row["updated_at"],
            {"table": "performance_connections", "id": str(row["id"]), "provider": row["provider"]},
            workspace_id=row["workspace_id"],
        )
        for row in rows
    ]


DETECTORS: dict[str, Detector] = {
    "proposta_ganha": proposta_ganha,
    "cliente_ativado": cliente_ativado,
    "entrega_aceita": entrega_aceita,
    "projeto_concluido": projeto_concluido,
    "prospect_aprovado": prospect_aprovado,
    "pico_de_propostas": pico_de_propostas,
    "integracao_conectada": integracao_conectada,
}

# Primeira varredura de um detector novo: olha 30 dias para trás. Suficiente
# para o mural não nascer vazio, curto o bastante para não enterrar o presente.
FIRST_SCAN_WINDOW = timedelta(days=30)
