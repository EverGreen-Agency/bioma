from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api.db import connect
from bioma_api.main import app
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
OPERATOR_EMAIL = "smoke-tasks-operator@bioma.example.com"
VIEWER_EMAIL = "smoke-tasks-viewer@bioma.example.com"
CLIENT_EMAIL = "smoke-tasks-client@bioma.example.com"
B_ONLY_EMAIL = "smoke-tasks-b-only@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert_status(response, 200, f"login {email}")


def assign(workspace_id, user_id, role: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            insert into workspace_assignments (workspace_id, user_id, role)
            values (%s, %s, %s)
            on conflict (workspace_id, user_id) where user_id is not null
            do update set role = excluded.role, updated_at = now()
            """,
            (workspace_id, user_id, role),
        )


# Decisao 13: tarefa de CLIENTE exige projeto, e o workspace de smoke e de
# cliente. Preenchido em main() com o projeto padrao do workspace.
PROJECT_ID = None


def task_payload(title: str, **updates) -> dict:
    payload = {
        "title": title,
        "description": "Smoke tasks",
        "project_id": PROJECT_ID,
        "status": "pending",
        "group_status": "NOT_STARTED",
        "recurrence": "none",
        "custom_fields": [],
        "dependencies": [],
        "subtasks": [],
    }
    payload.update(updates)
    return payload


def main() -> None:
    workspace_a = create_smoke_workspace("Tasks A")
    global PROJECT_ID
    PROJECT_ID = str(workspace_a.project_id)
    workspace_b = create_smoke_workspace("Tasks B")
    emails = [OPERATOR_EMAIL, VIEWER_EMAIL, CLIENT_EMAIL, B_ONLY_EMAIL]
    operator_id = upsert_smoke_user(OPERATOR_EMAIL, "Tasks Operator", PASSWORD)
    viewer_id = upsert_smoke_user(VIEWER_EMAIL, "Tasks Viewer", PASSWORD)
    client_id = upsert_smoke_user(CLIENT_EMAIL, "Tasks Client", PASSWORD)
    b_only_id = upsert_smoke_user(B_ONLY_EMAIL, "Tasks B Only", PASSWORD)
    assign(workspace_a.workspace_id, operator_id, "operator")
    assign(workspace_a.workspace_id, viewer_id, "viewer")
    assign(workspace_b.workspace_id, b_only_id, "operator")
    grant_client_user(workspace_a, client_id)

    admin = TestClient(app)
    operator = TestClient(app)
    viewer = TestClient(app)
    client_user = TestClient(app)

    try:
        for http_client, email in (
            (admin, ADMIN_EMAIL),
            (operator, OPERATOR_EMAIL),
            (viewer, VIEWER_EMAIL),
            (client_user, CLIENT_EMAIL),
        ):
            login(http_client, email)

        list_a = admin.post(
            f"/workspaces/{workspace_a.workspace_id}/task-lists",
            json={"name": "Smoke A", "type": "growth"},
        )
        assert_status(list_a, 201, "admin creates list A")
        list_a_id = list_a.json()["id"]
        list_b = admin.post(
            f"/workspaces/{workspace_b.workspace_id}/task-lists",
            json={"name": "Smoke B", "type": "growth"},
        )
        assert_status(list_b, 201, "admin creates list B")
        list_b_id = list_b.json()["id"]

        assert_status(operator.get(f"/workspaces/{workspace_a.workspace_id}/task-lists"), 200, "operator reads A")
        assert_status(viewer.get(f"/workspaces/{workspace_a.workspace_id}/task-lists"), 200, "viewer reads A")
        assert_status(client_user.get(f"/workspaces/{workspace_a.workspace_id}/task-lists"), 200, "client reads A")
        assert_status(
            viewer.post(f"/workspaces/{workspace_a.workspace_id}/task-lists", json={"name": "No", "type": "general"}),
            403,
            "viewer cannot create list",
        )
        assert_status(
            client_user.post(f"/task-lists/{list_a_id}/tasks", json=task_payload("No client write")),
            403,
            "client cannot mutate tasks",
        )
        assert_status(
            client_user.get(f"/workspaces/{workspace_b.workspace_id}/task-lists"),
            404,
            "client A cannot read workspace B",
        )
        assert_status(
            client_user.post(f"/task-lists/{list_b_id}/tasks", json=task_payload("Cross tenant mutation")),
            404,
            "client A cannot mutate workspace B",
        )

        with connect() as conn:
            clickup_task_id = conn.execute(
                """
                insert into eg_tasks (
                  list_id, title, status, group_status, recurrence, external_source, external_id
                ) values (%s, 'ClickUp projection', 'pending', 'NOT_STARTED', 'none', 'clickup', 'smoke-external')
                returning id
                """,
                (list_a_id,),
            ).fetchone()["id"]
        projected = operator.get(f"/task-lists/{list_a_id}/tasks")
        assert_status(projected, 200, "read ClickUp projection")
        assert next(row for row in projected.json() if row["id"] == str(clickup_task_id))["external_source"] == "clickup"
        assert_status(
            operator.patch(f"/tasks/{clickup_task_id}", json={"title": "Must stay external"}),
            409,
            "ClickUp projection is read only",
        )

        dependency = operator.post(f"/task-lists/{list_a_id}/tasks", json=task_payload("Dependency"))
        assert_status(dependency, 201, "operator creates dependency")
        dependency_id = dependency.json()["id"]
        created = operator.post(
            f"/task-lists/{list_a_id}/tasks",
            json=task_payload(
                "Main task",
                assignee_id=str(operator_id),
                owner_id=str(viewer_id),
                dependencies=[{"depends_on_task_id": dependency_id, "type": "waiting_on"}],
                subtasks=[{"title": "First", "is_completed": False}],
            ),
        )
        assert_status(created, 201, "operator creates full task")
        task = created.json()
        task_id = task["id"]
        assert task["dependencies"][0]["depends_on_task_id"] == dependency_id
        assert task["subtasks"][0]["title"] == "First"

        assert_status(
            operator.patch(f"/tasks/{task_id}", json={"owner_id": str(b_only_id)}),
            422,
            "owner outside workspace rejected",
        )
        # Projeto do workspace B, nao o global: a tarefa e de outro workspace,
        # e o guard de projeto cruzado recusa (corretamente) o projeto de A.
        other_task = admin.post(
            f"/task-lists/{list_b_id}/tasks",
            json=task_payload("B task", project_id=str(workspace_b.project_id)),
        )
        assert_status(other_task, 201, "admin creates B task")
        assert_status(
            operator.patch(
                f"/tasks/{task_id}",
                json={"dependencies": [{"depends_on_task_id": other_task.json()["id"], "type": "waiting_on"}]},
            ),
            422,
            "cross-workspace dependency rejected",
        )

        first_subtask = task["subtasks"][0]
        updated = operator.patch(
            f"/tasks/{task_id}",
            json={
                "dependencies": [{"depends_on_task_id": dependency_id, "type": "waiting_on"}],
                "subtasks": [
                    {"id": first_subtask["id"], "title": "First edited", "is_completed": True},
                    {"title": "Second", "is_completed": False},
                ],
            },
        )
        assert_status(updated, 200, "edit dependencies and subtasks")
        assert [(row["title"], row["is_completed"]) for row in updated.json()["subtasks"]] == [
            ("First edited", True),
            ("Second", False),
        ]

        added = operator.post(f"/tasks/{task_id}/subtasks", json={"title": "Endpoint subtask"})
        assert_status(added, 201, "add subtask endpoint")
        toggled = operator.patch(f"/subtasks/{added.json()['id']}/toggle")
        assert_status(toggled, 200, "toggle subtask")
        assert toggled.json()["is_completed"] is True
        deleted_subtask = operator.delete(f"/subtasks/{added.json()['id']}")
        assert_status(deleted_subtask, 204, "delete subtask")
        assert deleted_subtask.content == b""

        recurring = operator.post(
            f"/task-lists/{list_a_id}/tasks",
            json=task_payload("Recurring smoke", recurrence="weekly", due_date="2026-07-21T12:00:00Z"),
        )
        assert_status(recurring, 201, "create recurring task")
        recurring_id = recurring.json()["id"]
        for attempt in (1, 2):
            response = operator.patch(f"/tasks/{recurring_id}", json={"group_status": "DONE"})
            assert_status(response, 200, f"complete recurring task attempt {attempt}")
        listed = operator.get(f"/task-lists/{list_a_id}/tasks")
        assert_status(listed, 200, "list after recurrence")
        assert sum(row["title"] == "Recurring smoke" for row in listed.json()) == 2

        deleted = operator.delete(f"/tasks/{task_id}")
        assert_status(deleted, 204, "delete task")
        assert deleted.content == b""
        assert_status(operator.patch(f"/tasks/{task_id}", json={"title": "Gone"}), 404, "deleted task is gone")
    finally:
        cleanup_smoke_data([workspace_a.organization_id, workspace_b.organization_id], emails)

    print("tasks smoke ok")


if __name__ == "__main__":
    main()
