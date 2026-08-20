from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_workspace_capability
from bioma_api.db import connect
from bioma_api.repositories import tasks as tasks_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.tasks import (
    AssignableUser,
    MyTaskSummary,
    Task,
    TaskComment,
    TaskCommentCreate,
    TaskCreate,
    TaskList,
    TaskListCreate,
    TaskUpdate,
)

# Tipos utilitários
from typing import Optional
from uuid import UUID as _UUID


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _authorize(context, user: CurrentUserResponse, capability: str, detail: str) -> dict:
    if not context:
        raise _not_found(detail)
    resolved = dict(context)
    require_workspace_capability(resolved, user, capability)
    return resolved


def _require_local_task(context: dict) -> None:
    if context.get("external_source") == "clickup":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tarefas importadas do ClickUp são projeções somente leitura; altere a fonte de verdade no ClickUp.",
        )


def _validate_people(conn, workspace_id: UUID, values: dict) -> None:
    for field in ("assignee_id", "owner_id"):
        user_id = values.get(field)
        if user_id is not None and not tasks_repo.user_can_belong_to_workspace(conn, workspace_id, user_id):
            label = "Responsável" if field == "assignee_id" else "Owner"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{label} precisa pertencer ao mesmo tenant/workspace da tarefa.",
            )


def _validate_dates(conn, values: dict, task_id: UUID | None = None) -> None:
    """Início depois do vencimento é 422 amigável, não 500 da constraint.

    No update parcial, o outro lado da comparação pode estar só no banco —
    por isso busca o valor atual quando falta no payload.
    """
    start = values.get("start_date")
    due = values.get("due_date")
    if (start is None or due is None) and task_id is not None and ("start_date" in values or "due_date" in values):
        row = conn.execute("select start_date, due_date from eg_tasks where id = %s", (task_id,)).fetchone()
        if row:
            start = start if "start_date" in values else row["start_date"]
            due = due if "due_date" in values else row["due_date"]
    if start is not None and due is not None and start > due:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data de início não pode ser depois do vencimento.",
        )


def _validate_project(conn, workspace_id: UUID, values: dict, context: dict) -> None:
    """Projeto tem que ser do mesmo workspace — e, em CLIENTE, é obrigatório.

    Decisão 13 (2026-08-08). Tarefa de cliente sem projeto perde o contexto que
    liga comunicação, planejamento, documento e proposta — é esse elo que
    alimenta o copiloto, o benchmark da EG e a geração de conteúdo. Cada tarefa
    que nasce órfã é histórico que fica caro de reconstruir depois.

    Na Operação EG continua OPCIONAL, de propósito: demanda interna legítima
    existe sem projeto (treinamento, hackathon, social da casa). Exigir projeto
    ali obrigaria a inventar um projeto "diversos", que polui exatamente o
    contexto que esta regra existe para melhorar.

    `context` NAO tem valor padrao e o tipo e lido por colchete, de proposito.
    A primeira versao aceitava `context=None` e usava `.get()`: dois dos tres
    caminhos de escrita nao passavam contexto, e as queries de contexto nem
    selecionavam `w.kind` — a regra ficou MORTA, liberando tudo, sem erro
    nenhum. Faltando o dado agora, explode.
    """
    project_id = values.get("project_id")

    if project_id is None:
        if context["workspace_kind"] == "client":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Tarefa de cliente precisa estar vinculada a um projeto. "
                    "Crie o projeto em Projetos e contratos e vincule a tarefa a ele."
                ),
            )
        return

    if not tasks_repo.project_belongs_to_workspace(conn, workspace_id, project_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O projeto precisa pertencer ao mesmo workspace da tarefa.",
        )


def _validate_parent(conn, workspace_id: UUID, values: dict, task_id: UUID | None = None) -> None:
    parent_id = values.get("parent_task_id")
    if parent_id is None:
        return
    if task_id is not None and parent_id == task_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uma tarefa não pode ser subtarefa de si mesma.",
        )
    if tasks_repo.task_ids_in_workspace(conn, workspace_id, [parent_id]) != {parent_id}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A tarefa-pai precisa pertencer ao mesmo workspace.",
        )
    if task_id is not None and tasks_repo.parent_would_cycle(conn, task_id, parent_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O vínculo criaria um ciclo entre tarefa e subtarefa.",
        )


def _validate_dependencies(
    conn,
    workspace_id: UUID,
    dependencies: list[dict],
    task_id: UUID | None = None,
) -> None:
    dependency_ids = [dependency["depends_on_task_id"] for dependency in dependencies]
    if len(dependency_ids) != len(set(dependency_ids)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dependência duplicada.")
    if task_id is not None and task_id in dependency_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Uma tarefa não pode depender de si mesma.")
    if tasks_repo.task_ids_in_workspace(conn, workspace_id, dependency_ids) != set(dependency_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Todas as dependências precisam pertencer ao mesmo workspace.",
        )
    if task_id is not None:
        for dependency_id in dependency_ids:
            if tasks_repo.dependency_would_cycle(conn, task_id, dependency_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A dependência criaria um ciclo entre tarefas.",
                )


def list_task_lists(workspace_id: UUID, user: CurrentUserResponse) -> list[TaskList]:
    with connect() as conn:
        context = tasks_repo.find_workspace_context(conn, workspace_id, is_platform_admin(user), user.id)
        _authorize(context, user, "view", "Workspace não encontrado.")
        return [TaskList(**row) for row in tasks_repo.list_task_lists(conn, workspace_id)]


def create_task_list(workspace_id: UUID, data: TaskListCreate, user: CurrentUserResponse) -> TaskList:
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nome da lista é obrigatório.")
    with connect() as conn:
        context = tasks_repo.find_workspace_context(conn, workspace_id, is_platform_admin(user), user.id)
        _authorize(context, user, "manage_work", "Workspace não encontrado.")
        return TaskList(**tasks_repo.create_task_list(conn, workspace_id, name, data.type))


def list_workspace_tasks(
    workspace_id: UUID,
    user: CurrentUserResponse,
    discipline: Optional[str] = None,
    project_id: Optional[_UUID] = None,
) -> list[Task]:
    """Lista tarefas diretamente do workspace, sem precisar de lista.
    Substitui o GET /task-lists/{id}/tasks como ponto de entrada principal.
    """
    with connect() as conn:
        context = tasks_repo.find_workspace_context(conn, workspace_id, is_platform_admin(user), user.id)
        _authorize(context, user, "view", "Workspace não encontrado.")
        rows = tasks_repo.list_workspace_tasks(conn, workspace_id, discipline, project_id)
    if not _sees_internal_tasks(user):
        rows = [row for row in rows if row["client_visible"]]
    return [Task(**row) for row in rows]


def create_workspace_task(workspace_id: UUID, data: TaskCreate, user: CurrentUserResponse) -> Task:
    """Cria tarefa no workspace sem exigir lista. O campo `discipline` (growth/tech)
    substitui o tipo da lista como forma de categorizar o trabalho.
    """
    values = data.model_dump()
    values["title"] = values["title"].strip()
    if not values["title"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Título da tarefa é obrigatório.")
    custom_fields = [field.model_dump() for field in data.custom_fields]
    dependencies = [dep.model_dump() for dep in data.dependencies]
    subtasks = [sub.model_dump() for sub in data.subtasks]
    with connect() as conn:
        context = tasks_repo.find_workspace_context(conn, workspace_id, is_platform_admin(user), user.id)
        _authorize(context, user, "manage_work", "Workspace não encontrado.")
        _validate_people(conn, workspace_id, values)
        _validate_dates(conn, values)
        _validate_project(conn, workspace_id, values, context)
        _validate_parent(conn, workspace_id, values)
        _validate_dependencies(conn, workspace_id, dependencies)
        row = tasks_repo.create_task_in_workspace(conn, workspace_id, values)
        task_id = row["id"]
        tasks_repo.replace_custom_fields(conn, task_id, custom_fields)
        tasks_repo.replace_dependencies(conn, task_id, dependencies)
        tasks_repo.replace_subtasks(conn, task_id, subtasks)
        return Task(**tasks_repo.get_task(conn, task_id))


def get_tasks_in_list(list_id: UUID, user: CurrentUserResponse) -> list[Task]:
    with connect() as conn:
        context = tasks_repo.find_list_context(conn, list_id, is_platform_admin(user), user.id)
        _authorize(context, user, "view", "Lista de tarefas não encontrada.")
        rows = tasks_repo.list_tasks(conn, list_id)
    # Filtro no backend, não na tela: esconder no front deixaria a tarefa
    # interna viajando no payload para o navegador do cliente.
    if not _sees_internal_tasks(user):
        rows = [row for row in rows if row["client_visible"]]
    return [Task(**row) for row in rows]


def _sees_internal_tasks(user: CurrentUserResponse) -> bool:
    """Quem é da EG vê tudo; usuário do cliente só o que é visível a ele."""
    if is_platform_admin(user):
        return True
    return any(
        organization.role in ("eg_admin", "tenant_admin") or organization.slug == "eg"
        for organization in user.organizations
    )


def create_task(list_id: UUID, data: TaskCreate, user: CurrentUserResponse) -> Task:
    values = data.model_dump()
    values["title"] = values["title"].strip()
    if not values["title"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Título da tarefa é obrigatório.")
    custom_fields = [field.model_dump() for field in data.custom_fields]
    dependencies = [dependency.model_dump() for dependency in data.dependencies]
    subtasks = [subtask.model_dump() for subtask in data.subtasks]
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_list_context(conn, list_id, is_platform_admin(user), user.id),
            user,
            "manage_work",
            "Lista de tarefas não encontrada.",
        )
        _validate_people(conn, context["workspace_id"], values)
        _validate_dates(conn, values)
        _validate_project(conn, context["workspace_id"], values, context)
        _validate_parent(conn, context["workspace_id"], values)
        _validate_dependencies(conn, context["workspace_id"], dependencies)
        row = tasks_repo.create_task(conn, list_id, values)
        task_id = row["id"]
        tasks_repo.replace_custom_fields(conn, task_id, custom_fields)
        tasks_repo.replace_dependencies(conn, task_id, dependencies)
        tasks_repo.replace_subtasks(conn, task_id, subtasks)
        return Task(**tasks_repo.get_task(conn, task_id))


def update_task(task_id: UUID, data: TaskUpdate, user: CurrentUserResponse) -> Task:
    updates = data.model_dump(exclude_unset=True)
    custom_fields = updates.pop("custom_fields", None)
    dependencies = updates.pop("dependencies", None)
    subtasks = updates.pop("subtasks", None)
    if "title" in updates:
        updates["title"] = updates["title"].strip()
        if not updates["title"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Título da tarefa é obrigatório.")
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_task_context(conn, task_id, is_platform_admin(user), user.id),
            user,
            "manage_work",
            "Tarefa não encontrada.",
        )
        _require_local_task(context)
        _validate_people(conn, context["workspace_id"], updates)
        _validate_dates(conn, updates, task_id)
        _validate_project(conn, context["workspace_id"], updates, context)
        _validate_parent(conn, context["workspace_id"], updates, task_id)
        if dependencies is not None:
            _validate_dependencies(conn, context["workspace_id"], dependencies, task_id)
        if not tasks_repo.update_task(conn, task_id, updates):
            raise _not_found("Tarefa não encontrada.")
        if custom_fields is not None:
            tasks_repo.replace_custom_fields(conn, task_id, custom_fields)
        if dependencies is not None:
            tasks_repo.replace_dependencies(conn, task_id, dependencies)
        if subtasks is not None:
            try:
                tasks_repo.replace_subtasks(conn, task_id, subtasks)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Subtarefa não pertence à tarefa informada.",
                ) from exc
        task = tasks_repo.get_task(conn, task_id)
        if task["group_status"] in {"DONE", "CLOSED"} and task.get("recurrence") in {"weekly", "monthly"}:
            current_due = task.get("due_date") or datetime.now(timezone.utc)
            task["next_due_date"] = current_due + timedelta(days=7 if task["recurrence"] == "weekly" else 30)
            successor = tasks_repo.create_recurring_successor(conn, task)
            if successor:
                tasks_repo.copy_recurring_children(conn, task_id, successor["id"])
        return Task(**task)


def delete_task(task_id: UUID, user: CurrentUserResponse) -> None:
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_task_context(conn, task_id, is_platform_admin(user), user.id),
            user,
            "manage_work",
            "Tarefa não encontrada.",
        )
        _require_local_task(context)
        if not tasks_repo.delete_task(conn, task_id):
            raise _not_found("Tarefa não encontrada.")


def add_subtask(task_id: UUID, title: str, user: CurrentUserResponse) -> dict:
    clean_title = title.strip()
    if not clean_title:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Título da subtarefa é obrigatório.")
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_task_context(conn, task_id, is_platform_admin(user), user.id),
            user,
            "manage_work",
            "Tarefa não encontrada.",
        )
        _require_local_task(context)
        return dict(tasks_repo.add_subtask(conn, task_id, clean_title))


def toggle_subtask(subtask_id: UUID, user: CurrentUserResponse) -> dict:
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_subtask_context(conn, subtask_id, is_platform_admin(user), user.id),
            user,
            "manage_work",
            "Subtarefa não encontrada.",
        )
        _require_local_task(context)
        row = tasks_repo.toggle_subtask(conn, subtask_id)
        if not row:
            raise _not_found("Subtarefa não encontrada.")
        return dict(row)


def delete_subtask(subtask_id: UUID, user: CurrentUserResponse) -> None:
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_subtask_context(conn, subtask_id, is_platform_admin(user), user.id),
            user,
            "manage_work",
            "Subtarefa não encontrada.",
        )
        _require_local_task(context)
        if not tasks_repo.delete_subtask(conn, subtask_id):
            raise _not_found("Subtarefa não encontrada.")


def list_task_comments(task_id: UUID, user: CurrentUserResponse) -> list[TaskComment]:
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_task_context(conn, task_id, is_platform_admin(user), user.id),
            user,
            "view",
            "Tarefa não encontrada.",
        )
        # client_user só vê o que foi explicitamente marcado como visível.
        include_internal = context.get("access_role") != "client_user"
        rows = tasks_repo.list_task_comments(conn, task_id, include_internal)
    return [TaskComment(**row) for row in rows]


def create_task_comment(task_id: UUID, data: TaskCommentCreate, user: CurrentUserResponse) -> TaskComment:
    body = data.body.strip()
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Comentário vazio.")
    with connect() as conn:
        context = _authorize(
            tasks_repo.find_task_context(conn, task_id, is_platform_admin(user), user.id),
            user,
            "view",
            "Tarefa não encontrada.",
        )
        # Cliente comenta na própria tarefa (é parte do fluxo de aprovação),
        # mas não decide visibilidade: o que ele escreve é sempre visível a ele.
        client_visible = True if context.get("access_role") == "client_user" else data.client_visible
        row = tasks_repo.create_task_comment(conn, task_id, user.id, body, client_visible)
    return TaskComment(**row)


def delete_task_comment(comment_id: UUID, user: CurrentUserResponse) -> None:
    with connect() as conn:
        owner = tasks_repo.find_comment_task(conn, comment_id)
        if not owner:
            raise _not_found("Comentário não encontrado.")
        _authorize(
            tasks_repo.find_task_context(conn, owner["task_id"], is_platform_admin(user), user.id),
            user,
            "view",
            "Comentário não encontrado.",
        )
        if not tasks_repo.delete_task_comment(conn, comment_id, user.id, is_platform_admin(user)):
            # Não distingue "não existe" de "não é seu": não confirma a
            # existência de comentário que o usuário não pode apagar.
            raise _not_found("Comentário não encontrado.")


def list_my_tasks(user: CurrentUserResponse) -> list[MyTaskSummary]:
    """Não recebe workspace: é a visão pessoal, atravessa a carteira toda e o
    workspace interno da EG. O escopo é garantido na própria query."""
    with connect() as conn:
        rows = tasks_repo.list_my_tasks(conn, user.id, is_platform_admin(user))
    return [MyTaskSummary(**row) for row in rows]


def list_assignable_users(workspace_id: UUID, user: CurrentUserResponse) -> list[AssignableUser]:
    with connect() as conn:
        context = tasks_repo.find_workspace_context(conn, workspace_id, is_platform_admin(user), user.id)
        _authorize(context, user, "view", "Workspace não encontrado.")
        rows = tasks_repo.list_assignable_users(conn, workspace_id)
    return [AssignableUser(**row) for row in rows]
