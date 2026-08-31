"""Painel de prova: o que a EG entrega e o que ela mantém no ar.

Inspirado no painel público da HeroSpark, com uma diferença que é o ponto
inteiro: **todo número aqui tem origem verificável**, e o que não tem não
aparece.

Três blocos, três fontes:

- disponibilidade → `uptime_snapshots`, alimentado por um prober EXTERNO. Se o
  Bioma medisse a si mesmo, uma queda total registraria 100%;
- entregas → `deliverables` concluídas, que é o registro que já existe;
- correções → `improvement_requests` resolvidas, com o tempo real até a
  resolução.

Onde falta dado, a resposta diz que falta em vez de estimar. Um painel de
confiabilidade que preenche buraco com palpite destrói exatamente a coisa que
ele existe para construir.
"""

from datetime import date, timedelta

from bioma_api.access import require_platform_admin
from bioma_api.db import connect
from bioma_api.repositories import proof as repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.proof import (
    ProofDelivery,
    ProofFix,
    ProofPanel,
    ProofUptime,
)


def get_panel(user: CurrentUserResponse, weeks: int = 12) -> ProofPanel:
    require_platform_admin(user)
    today = date.today()

    with connect() as conn:
        uptime_rows = repo.latest_uptime(conn)
        daily_rows = repo.daily_uptime(conn, today - timedelta(days=89), today)
        deliveries = repo.recent_deliveries(conn, limit=weeks * 2)
        fixes = repo.recent_fixes(conn, limit=10)
        open_issues = repo.open_issue_count(conn)

    uptime = [
        ProofUptime(
            monitor_id=row["monitor_id"],
            monitor_name=row["monitor_name"],
            kind=row["kind"],
            window_days=row["window_days"],
            availability=float(row["availability"]),
            number_of_incidents=row["number_of_incidents"],
            total_downtime_seconds=row["total_downtime_seconds"],
            measured_since=row["measured_since"],
            collected_at=row["collected_at"],
        )
        for row in uptime_rows
    ]

    return ProofPanel(
        generated_at=today,
        # Vazio = ninguém mediu ainda. A tela precisa distinguir isso de "100%",
        # que é o erro que faz um painel de uptime perder a credibilidade.
        uptime=uptime,
        daily_uptime=[
            {"date": row["snapshot_date"], "availability": float(row["availability"])}
            for row in daily_rows
        ],
        deliveries=[
            ProofDelivery(
                id=row["id"],
                title=row["title"],
                completed_at=row["completed_at"],
                workspace_name=row["workspace_name"],
            )
            for row in deliveries
        ],
        open_issues=open_issues,
        fixes=[
            ProofFix(
                id=row["id"],
                title=row["title"],
                resolved_at=row["resolved_at"],
                minutes_to_resolve=row["minutes_to_resolve"],
            )
            for row in fixes
        ],
    )
