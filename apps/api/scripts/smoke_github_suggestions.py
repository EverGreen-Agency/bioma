"""Smoke da conciliação GitHub → entrega (issue fechada SUGERE conclusão).

Decisão do Eduardo (DECISOES-ABERTAS #9): **sugerir, não concluir**. Concluir
entrega tem efeito contratual e já tem aceite separado; um robô concluindo
porque alguém fechou uma issue inverteria essa regra pela porta dos fundos.

O que este smoke protege são as REGRAS DE EXCLUSÃO, que é onde uma sugestão
vira ruído e o time para de olhar:
- issue aberta não sugere nada;
- entrega `done` não volta a ser sugerida;
- entrega `blocked` com issue fechada SUGERE (travada lá fora resolvida é
  justamente o caso que vale trazer para a mesa — `done` é o único terminal);
- entrega sem issue ligada nunca aparece;
- e o principal: a chamada NÃO altera o estado da entrega.

O GitHub é mockado no nível do cliente HTTP: o objetivo é provar a regra de
conciliação, não a rede.
"""

from pathlib import Path
import atexit
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect
from bioma_api.schemas.github import GitHubProjectActivity
from bioma_api.services import github as github_service
from smoke_support import cleanup_smoke_data, create_smoke_workspace

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"


class FakeUser:
    """Basta o que `require_platform_admin` e o resolvedor de projeto leem."""

    def __init__(self, user_id):
        self.id = user_id


def main() -> None:
    workspace = create_smoke_workspace("GHSUG")
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], []))

    with connect() as conn:
        admin_id = conn.execute(
            "select id from users where lower(email) = lower(%s)", (ADMIN_EMAIL,)
        ).fetchone()["id"]
        project_id = conn.execute(
            """
            insert into projects
              (tenant_organization_id, organization_id, workspace_id, name, project_type, status, created_by)
            values (%s, %s, %s, 'Projeto GH Smoke', 'tech', 'active', %s)
            returning id
            """,
            (workspace.tenant_id, workspace.organization_id, workspace.workspace_id, admin_id),
        ).fetchone()["id"]

        def new_deliverable(title: str, status: str, issue: int | None) -> str:
            return conn.execute(
                """
                insert into deliverables
                  (organization_id, project_id, title, status, github_issue_number, github_issue_url)
                values (%s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    workspace.organization_id, project_id, title, status, issue,
                    f"https://github.com/eg/repo/issues/{issue}" if issue else None,
                ),
            ).fetchone()["id"]

        aberta_fechou = new_deliverable("Entrega com issue fechada", "in_progress", 10)
        aberta_issue_aberta = new_deliverable("Entrega com issue aberta", "in_progress", 11)
        ja_concluida = new_deliverable("Entrega ja concluida", "done", 12)
        bloqueada = new_deliverable("Entrega bloqueada", "blocked", 13)
        sem_issue = new_deliverable("Entrega sem issue", "in_progress", None)

    # GitHub diz: 10, 12 e 13 fechadas; 11 aberta.
    def fake_activity(pid, user, limit):
        def issue(number, state):
            return type("I", (), {"number": number, "state": state, "title": f"Issue #{number}"})()
        return GitHubProjectActivity.model_construct(
            project_id=pid,
            repository="eg/repo",
            default_branch="main",
            fetched_at=datetime.now(timezone.utc),
            issues=[issue(10, "closed"), issue(11, "open"), issue(12, "closed"), issue(13, "closed")],
            pull_requests=[],
            commits=[],
        )

    original = github_service.get_activity
    github_service.get_activity = fake_activity
    try:
        result = github_service.list_completion_suggestions(project_id, FakeUser(admin_id))
        ids = {str(item.deliverable_id) for item in result.suggestions}

        assert str(aberta_fechou) in ids, "issue fechada + entrega aberta TEM que sugerir"
        assert str(aberta_issue_aberta) not in ids, "issue ainda aberta nao pode sugerir conclusao"
        assert str(ja_concluida) not in ids, "entrega ja concluida nao pode voltar a ser sugerida"
        # `blocked` NAO e' terminal: entrega travada cuja issue ja' fechou e'
        # exatamente o caso que vale trazer para a mesa.
        assert str(bloqueada) in ids, "entrega bloqueada com issue fechada TEM que sugerir"
        assert str(sem_issue) not in ids, "entrega sem issue nao tem como divergir"
        assert len(result.suggestions) == 2, f"esperava 2 sugestoes (in_progress e blocked): {ids}"
        print(f"regras de exclusao OK — 2 sugestoes entre 5 entregas ({result.repository})")

        # O ponto da decisão #9: sugerir NÃO altera nada.
        with connect() as conn:
            status_depois = conn.execute(
                "select status, completed_at from deliverables where id = %s", (aberta_fechou,)
            ).fetchone()
        assert status_depois["status"] == "in_progress" and status_depois["completed_at"] is None, (
            f"sugerir nao pode concluir a entrega: {status_depois}"
        )
        print("sugerir nao altera o estado da entrega (decisao #9) OK")

        item = next(i for i in result.suggestions if i.issue_number == 10)
        assert item.issue_number == 10 and item.issue_url and item.issue_title, item
        print(f"sugestao carrega a evidencia: issue #{item.issue_number} — {item.issue_title} OK")
    finally:
        github_service.get_activity = original
        with connect() as conn:
            conn.execute("delete from deliverables where project_id = %s", (project_id,))
            conn.execute("delete from projects where id = %s", (project_id,))
        cleanup_smoke_data([workspace.organization_id], [])
    print("limpeza OK — smoke_github_suggestions passou")


if __name__ == "__main__":
    main()
