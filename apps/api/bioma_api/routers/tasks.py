from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from bioma_api.auth import current_user_from_request
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
from bioma_api.services import tasks as tasks_service

router = APIRouter(prefix="", tags=["tasks"])

class SubtaskCreatePayload(BaseModel):
    title: str

# ---------------------------------------------------------------------------
# Rotas novas: tarefas direto no workspace (sem precisar de lista)
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/tasks", response_model=list[Task])
def list_workspace_tasks(
    workspace_id: UUID,
    discipline: Optional[str] = Query(None, description="Filtrar por disciplina: growth ou tech"),
    project_id: Optional[UUID] = Query(None),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[Task]:
    return tasks_service.list_workspace_tasks(workspace_id, user, discipline, project_id)

@router.post("/workspaces/{workspace_id}/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_workspace_task(
    workspace_id: UUID,
    data: TaskCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> Task:
    return tasks_service.create_workspace_task(workspace_id, data, user)

# ---------------------------------------------------------------------------
# Rotas legadas: lista de tarefas (mantidas para compat com dados existentes)
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/task-lists", response_model=list[TaskList])
def list_task_lists(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TaskList]:
    return tasks_service.list_task_lists(workspace_id, user)

@router.post("/workspaces/{workspace_id}/task-lists", response_model=TaskList, status_code=status.HTTP_201_CREATED)
def create_task_list(
    workspace_id: UUID,
    data: TaskListCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> TaskList:
    return tasks_service.create_task_list(workspace_id, data, user)

@router.get("/task-lists/{list_id}/tasks", response_model=list[Task])
def list_tasks(
    list_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[Task]:
    return tasks_service.get_tasks_in_list(list_id, user)

@router.post("/task-lists/{list_id}/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    list_id: UUID,
    data: TaskCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> Task:
    return tasks_service.create_task(list_id, data, user)

@router.patch("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> Task:
    return tasks_service.update_task(task_id, data, user)

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    tasks_service.delete_task(task_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/tasks/{task_id}/subtasks", status_code=status.HTTP_201_CREATED)
def add_subtask(
    task_id: UUID,
    payload: SubtaskCreatePayload,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return tasks_service.add_subtask(task_id, payload.title, user)

@router.patch("/subtasks/{subtask_id}/toggle")
def toggle_subtask(
    subtask_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    return tasks_service.toggle_subtask(subtask_id, user)

@router.delete("/subtasks/{subtask_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subtask(
    subtask_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    tasks_service.delete_subtask(subtask_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/tasks/{task_id}/comments", response_model=list[TaskComment])
def list_task_comments(
    task_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[TaskComment]:
    return tasks_service.list_task_comments(task_id, user)

@router.post("/tasks/{task_id}/comments", response_model=TaskComment, status_code=status.HTTP_201_CREATED)
def create_task_comment(
    task_id: UUID,
    data: TaskCommentCreate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> TaskComment:
    return tasks_service.create_task_comment(task_id, data, user)

@router.delete("/task-comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_comment(
    comment_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
):
    tasks_service.delete_task_comment(comment_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/tasks/me", response_model=list[MyTaskSummary])
def list_my_tasks(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[MyTaskSummary]:
    return tasks_service.list_my_tasks(user)

@router.get("/workspaces/{workspace_id}/assignable-users", response_model=list[AssignableUser])
def list_assignable_users(
    workspace_id: UUID,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> list[AssignableUser]:
    return tasks_service.list_assignable_users(workspace_id, user)
