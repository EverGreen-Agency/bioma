from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_workspace_capability
from bioma_api.config import get_settings
from bioma_api.db import connect
from bioma_api.integrations.github import GitHubClient, GitHubReadError, GitHubWriteError
from bioma_api.repositories import github as github_repo
from bioma_api.repositories import projects as project_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.github import (
    GitHubConnectionInput,
    GitHubConnectionSummary,
    GitHubActivitySyncRequest,
    GitHubActivitySyncResult,
    GitHubIssueCreateRequest,
    GitHubIssueLinkSummary,
    GitHubCompletionSuggestion,
    GitHubCompletionSuggestions,
    GitHubProjectActivity,
)


def get_connection(project_id: UUID, user: CurrentUserResponse) -> GitHubConnectionSummary:
    with connect() as conn:
        _project(conn, project_id, user, "view")
        row = github_repo.find_connection(conn, project_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório GitHub não configurado.")
    return _summary(row)


def upsert_connection(project_id: UUID, payload: GitHubConnectionInput, user: CurrentUserResponse) -> GitHubConnectionSummary:
    owner, repository = payload.repository.split("/", 1)
    with connect() as conn:
        project = _project(conn, project_id, user, "manage_work")
        if project["project_type"] != "tech":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub só pode ser ligado a projetos Tech.")
        row = github_repo.upsert_connection(conn, project_id, user.id, {
            "repository_owner": owner,
            "repository_name": repository,
            "default_branch": payload.default_branch,
            "status": payload.status,
        })
        github_repo.write_audit(conn, user.id, project["subject_organization_id"], "github.connection_upserted", {
            "project_id": str(project_id), "repository": payload.repository, "status": payload.status,
        })
    return _summary(row)


def get_activity(project_id: UUID, user: CurrentUserResponse, limit: int) -> GitHubProjectActivity:
    settings = get_settings()
    if not settings.github_api_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GITHUB_API_TOKEN não configurado.")
    with connect() as conn:
        _project(conn, project_id, user, "view")
        connection = github_repo.find_connection(conn, project_id)
    if not connection or connection["status"] != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório GitHub ativo não configurado.")
    client = GitHubClient(settings.github_api_token, settings.github_api_base_url)
    try:
        activity = client.project_activity(
            connection["repository_owner"], connection["repository_name"], connection["default_branch"], limit,
        )
    except GitHubReadError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        client.close()
    return GitHubProjectActivity(
        project_id=project_id,
        repository=f"{connection['repository_owner']}/{connection['repository_name']}",
        default_branch=connection["default_branch"],
        **activity,
    )


def create_issue_from_deliverable(
    deliverable_id: UUID, payload: GitHubIssueCreateRequest, user: CurrentUserResponse
) -> GitHubIssueLinkSummary:
    settings = get_settings()
    with connect() as conn:
        deliverable = github_repo.find_deliverable_for_issue(conn, deliverable_id)
        if not deliverable:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrega não encontrada.")
        if not deliverable["project_id"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Entrega não está ligada a um projeto Tech.",
            )
        project = _project(conn, deliverable["project_id"], user, "manage_work")
        if project["project_type"] != "tech":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GitHub só pode ser ligado a projetos Tech.")
        connection = github_repo.find_connection(conn, deliverable["project_id"])
        if not connection or connection["status"] != "active":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repositório GitHub ativo não configurado.")
        repository = f"{connection['repository_owner']}/{connection['repository_name']}"

        if deliverable["github_issue_number"] is not None:
            # Idempotente: uma entrega já ligada a uma issue nunca cria uma segunda ao reprocessar.
            return GitHubIssueLinkSummary(
                deliverable_id=deliverable_id,
                repository=repository,
                issue_number=deliverable["github_issue_number"],
                issue_url=deliverable["github_issue_url"],
            )

        if not settings.github_api_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="GITHUB_API_TOKEN não configurado.")
        if not github_repo.reserve_deliverable_issue(conn, deliverable_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A criação desta issue já está em andamento. Tente novamente em alguns minutos.",
            )
        owner = connection["repository_owner"]
        repository_name = connection["repository_name"]
        project_id = deliverable["project_id"]
        organization_id = project["subject_organization_id"]
        deliverable_title = deliverable["title"]

    marker = f"[Bioma:{deliverable_id}]"
    issue_title = f"{marker} {deliverable_title}"
    issue_body = "\n".join(part for part in (payload.body, "", f"Rastreio: {marker}") if part is not None)
    client = GitHubClient(settings.github_api_token, settings.github_api_base_url)
    try:
        issue = client.find_issue_by_title_prefix(owner, repository_name, marker)
        if issue is None:
            issue = client.create_issue(owner, repository_name, issue_title, issue_body)
    except (GitHubReadError, GitHubWriteError) as exc:
        with connect() as conn:
            github_repo.fail_deliverable_issue(conn, deliverable_id, str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    finally:
        client.close()

    with connect() as conn:
        github_repo.record_deliverable_issue(conn, deliverable_id, issue["number"], issue["url"])
        github_repo.write_audit(conn, user.id, organization_id, "github.issue_created", {
            "deliverable_id": str(deliverable_id), "project_id": str(project_id),
            "repository": repository, "issue_number": issue["number"],
        })

    return GitHubIssueLinkSummary(
        deliverable_id=deliverable_id, repository=repository, issue_number=issue["number"], issue_url=issue["url"],
    )


def publish_activity_update(
    project_id: UUID,
    payload: GitHubActivitySyncRequest,
    user: CurrentUserResponse,
) -> GitHubActivitySyncResult:
    with connect() as conn:
        project = _project(conn, project_id, user, "manage_work")
        existing = github_repo.find_activity_sync(conn, payload.idempotency_key)
        if existing:
            if existing["project_id"] != project_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A chave de idempotência já foi usada em outro projeto.",
                )
            return _activity_sync_result(existing)

    activity = get_activity(project_id, user, payload.limit)
    snapshot = activity.model_dump(mode="json")
    summary = payload.summary_override or _activity_summary(activity)
    detail = _activity_detail(activity)

    with connect() as conn:
        project = _project(conn, project_id, user, "manage_work")
        project_repo.lock_project(conn, project_id)
        existing = github_repo.find_activity_sync(conn, payload.idempotency_key)
        if existing:
            return _activity_sync_result(existing)
        update = project_repo.create_project_update(
            conn,
            project_id,
            user.id,
            {
                "kind": "progress",
                "summary": summary,
                "detail": detail,
                "client_visible": payload.client_visible,
            },
        )
        sync = github_repo.create_activity_sync(
            conn,
            project_id,
            payload.idempotency_key,
            snapshot,
            update["id"],
            user.id,
        )
        github_repo.write_audit(
            conn,
            user.id,
            project["subject_organization_id"],
            "github.activity_published_to_project",
            {
                "project_id": str(project_id),
                "project_update_id": str(update["id"]),
                "repository": activity.repository,
                "client_visible": payload.client_visible,
            },
        )
        row = {
            **dict(sync),
            "repository_owner": activity.repository.split("/", 1)[0],
            "repository_name": activity.repository.split("/", 1)[1],
            "client_visible": payload.client_visible,
        }
        return _activity_sync_result(row)


def _activity_summary(activity: GitHubProjectActivity) -> str:
    open_issues = sum(1 for issue in activity.issues if issue.state == "open")
    open_pulls = sum(1 for pull in activity.pull_requests if pull.state == "open")
    return (
        f"Atualização Tech: {len(activity.commits)} commits recentes, "
        f"{open_pulls} PRs abertos e {open_issues} issues abertas."
    )


def _activity_detail(activity: GitHubProjectActivity) -> str:
    sections = [f"Repositório: {activity.repository}"]
    if activity.pull_requests:
        sections.append(
            "Pull requests: " + "; ".join(
                f"#{item.number} {item.title} ({item.state})"
                for item in activity.pull_requests[:10]
            )
        )
    if activity.commits:
        sections.append(
            "Commits: " + "; ".join(
                f"{item.sha[:7]} {item.message}"
                for item in activity.commits[:10]
            )
        )
    if activity.issues:
        sections.append(
            "Issues: " + "; ".join(
                f"#{item.number} {item.title} ({item.state})"
                for item in activity.issues[:10]
            )
        )
    return "\n".join(sections)


def _activity_sync_result(row) -> GitHubActivitySyncResult:
    return GitHubActivitySyncResult(
        project_id=row["project_id"],
        project_update_id=row["project_update_id"],
        idempotency_key=row["idempotency_key"],
        repository=f"{row['repository_owner']}/{row['repository_name']}",
        client_visible=row["client_visible"],
        created_at=row["created_at"],
    )


def _project(conn, project_id: UUID, user: CurrentUserResponse, capability: str):
    project = project_repo.find_project_context(conn, project_id, is_platform_admin(user), user.id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    require_workspace_capability(project, user, capability)
    if project["access_role"] == "client_user" and not project["client_visible"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    return project


def _summary(row) -> GitHubConnectionSummary:
    return GitHubConnectionSummary(
        id=row["id"], project_id=row["project_id"],
        repository=f"{row['repository_owner']}/{row['repository_name']}",
        default_branch=row["default_branch"], status=row["status"], updated_at=row["updated_at"],
    )


def list_completion_suggestions(project_id: UUID, user: CurrentUserResponse) -> GitHubCompletionSuggestions:
    """Entregas cuja issue já foi fechada no GitHub mas que continuam abertas aqui.

    Decisão do Eduardo (DECISOES-ABERTAS #9): **sugerir, não concluir**.
    Concluir entrega tem efeito contratual e já tem aceite separado de
    propósito; um robô fechando entrega porque alguém fechou uma issue
    inverteria essa regra pela porta dos fundos.

    Sem estado novo e sem webhook: a divergência é CALCULADA na hora,
    comparando o que o GitHub diz com o que o Bioma tem. Guardar "sugestão
    pendente" numa tabela criaria uma terceira verdade para manter em dia — e
    a pergunta "esta issue está fechada?" já tem dono, que é o GitHub.
    """
    activity = get_activity(project_id, user, limit=100)
    closed_issues = {
        issue.number: issue for issue in activity.issues if issue.state == "closed"
    }
    with connect() as conn:
        rows = github_repo.list_deliverables_with_issues(conn, project_id)

    suggestions = [
        GitHubCompletionSuggestion(
            deliverable_id=row["id"],
            deliverable_title=row["title"],
            deliverable_status=row["status"],
            issue_number=row["github_issue_number"],
            issue_url=row["github_issue_url"],
            issue_title=closed_issues[row["github_issue_number"]].title,
        )
        for row in rows
        # `done` é o único estado terminal de entrega (o CHECK do banco aceita
        # planned/in_progress/waiting_approval/done/blocked). `blocked` fica de
        # fora da exclusão de propósito: entrega travada cuja issue já fechou é
        # justamente o caso que vale trazer para a mesa.
        if row["status"] != "done"
        and row["github_issue_number"] in closed_issues
    ]
    return GitHubCompletionSuggestions(
        project_id=project_id,
        repository=activity.repository,
        checked_at=activity.fetched_at,
        suggestions=suggestions,
    )
