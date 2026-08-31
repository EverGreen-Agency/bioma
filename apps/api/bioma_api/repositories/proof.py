from datetime import date
from typing import Any


def latest_uptime(conn) -> list[dict[str, Any]]:
    """A leitura mais recente de cada monitor por janela.

    `distinct on` em vez de `max(snapshot_date)` num subselect: a coleta roda
    uma vez por dia, mas rodar duas não pode produzir duas linhas na tela.
    """
    return conn.execute(
        """
        select distinct on (monitor_id, window_days)
          monitor_id, monitor_name, kind, window_days, availability,
          number_of_incidents, total_downtime_seconds, measured_since, collected_at
        from uptime_snapshots
        order by monitor_id, window_days, snapshot_date desc
        """
    ).fetchall()


def daily_uptime(conn, start: date, end: date) -> list[dict[str, Any]]:
    """A barra de dias. Só janela de 1 dia — misturar janelas aqui produziria
    uma barra onde cada quadradinho mede coisa diferente."""
    return conn.execute(
        """
        select snapshot_date, availability
        from uptime_snapshots
        where window_days = 1 and snapshot_date between %s and %s
        order by snapshot_date asc
        """,
        (start, end),
    ).fetchall()


def recent_deliveries(conn, limit: int = 24) -> list[dict[str, Any]]:
    """Entregas concluídas — a linha de produção.

    Sai de `deliverables`, que é o registro que já existe; nada de contador
    paralelo que precise ser mantido à mão e que divergiria na primeira semana.
    """
    return conn.execute(
        """
        select d.id, d.title, d.completed_at, coalesce(w.name, o.name) as workspace_name
        from deliverables d
        join organizations o on o.id = d.organization_id
        left join workspaces w on w.subject_organization_id = d.organization_id
        where d.status = 'done' and d.completed_at is not null
        order by d.completed_at desc
        limit %s
        """,
        (limit,),
    ).fetchall()


def open_issue_count(conn) -> int:
    row = conn.execute(
        "select count(*)::int as total from improvement_requests where status in ('pending', 'in_review')"
    ).fetchone()
    return row["total"] if row else 0


def recent_fixes(conn, limit: int = 10) -> list[dict[str, Any]]:
    """Correções resolvidas, com o tempo REAL até a resolução.

    O minuto sai de `reviewed_at - created_at`, não de um campo digitado: número
    de tempo de resposta que alguém preenche à mão vira número de marketing.
    """
    return conn.execute(
        """
        select
          id, title, reviewed_at as resolved_at,
          greatest(round(extract(epoch from (reviewed_at - created_at)) / 60)::int, 0) as minutes_to_resolve
        from improvement_requests
        where status = 'accepted' and reviewed_at is not null
        order by reviewed_at desc
        limit %s
        """,
        (limit,),
    ).fetchall()
