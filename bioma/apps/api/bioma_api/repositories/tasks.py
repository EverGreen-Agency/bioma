from collections.abc import Iterable
from uuid import UUID


TASK_COLUMNS = """
  id, list_id, workspace_id, discipline, project_id, parent_task_id, title, description, status,
  group_status, priority, assignee_id, owner_id, start_date, due_date,
  recurrence, external_source, external_id, client_visible, created_at, updated_at
"""


def find_workspace_context(conn, workspace_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select w.id as workspace_id, w.kind as workspace_kind,
          w.tenant_organization_id, w.subject_organization_id,
          case when %s then 'platform_admin' else workspace_access_role(w.id, %s) end as access_role
        from workspaces w
        where w.id = %s
          and w.status = 'active'
          and (%s or workspace_access_role(w.id, %s) is not null)
        """,
        (is_admin, user_id, workspace_id, is_admin, user_id),
    ).fetchone()


def find_list_context(conn, list_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select l.id as list_id, l.workspace_id, w.kind as workspace_kind,
          w.tenant_organization_id, w.subject_organization_id,
          case when %s then 'platform_admin' else workspace_access_role(w.id, %s) end as access_role
        from eg_task_lists l
        join workspaces w on w.id = l.workspace_id and w.status = 'active'
        where l.id = %s
          and (%s or workspace_access_role(w.id, %s) is not null)
        """,
        (is_admin, user_id, list_id, is_admin, user_id),
    ).fetchone()


def find_task_context(conn, task_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select t.id as task_id, t.group_status, t.external_source, t.list_id,
          coalesce(t.workspace_id, l.workspace_id) as workspace_id, w.kind as workspace_kind,
          w.tenant_organization_id, w.subject_organization_id,
          case when %s then 'platform_admin' else workspace_access_role(w.id, %s) end as access_role
        from eg_tasks t
        left join eg_task_lists l on l.id = t.list_id
        join workspaces w on w.id = coalesce(t.workspace_id, l.workspace_id) and w.status = 'active'
        where t.id = %s
          and (%s or workspace_access_role(w.id, %s) is not null)
        """,
        (is_admin, user_id, task_id, is_admin, user_id),
    ).fetchone()


def find_subtask_context(conn, subtask_id: UUID, is_admin: bool, user_id: UUID):
    return conn.execute(
        """
        select s.id as subtask_id, s.task_id, t.external_source,
          coalesce(t.workspace_id, l.workspace_id) as workspace_id, w.kind as workspace_kind,
          w.tenant_organization_id, w.subject_organization_id,
          case when %s then 'platform_admin' else workspace_access_role(w.id, %s) end as access_role
        from eg_task_subtasks s
        join eg_tasks t on t.id = s.task_id
        left join eg_task_lists l on l.id = t.list_id
        join workspaces w on w.id = coalesce(t.workspace_id, l.workspace_id) and w.status = 'active'
        where s.id = %s
          and (%s or workspace_access_role(w.id, %s) is not null)
        """,
        (is_admin, user_id, subtask_id, is_admin, user_id),
    ).fetchone()



def list_task_lists(conn, workspace_id: UUID):
    return conn.execute(
        """
        select id, workspace_id, name, type, created_at, updated_at
        from eg_task_lists
        where workspace_id = %s
        order by created_at, id
        """,
        (workspace_id,),
    ).fetchall()


def create_task_list(conn, workspace_id: UUID, name: str, list_type: str):
    return conn.execute(
        """
        insert into eg_task_lists (workspace_id, name, type)
        values (%s, %s, %s)
        returning id, workspace_id, name, type, created_at, updated_at
        """,
        (workspace_id, name, list_type),
    ).fetchone()


def list_workspace_tasks(conn, workspace_id: UUID, discipline: str | None = None, project_id: UUID | None = None):
    """Retorna todas as tarefas do workspace — sem precisar de list_id.
    Suporta filtro opcional por disciplina e/ou projeto.
    """
    clauses = ["t.workspace_id = %s"]
    params: list = [workspace_id]
    if discipline:
        clauses.append("t.discipline = %s")
        params.append(discipline)
    if project_id:
        clauses.append("t.project_id = %s")
        params.append(project_id)
    where = " and ".join(clauses)
    rows = conn.execute(
        f"""
        select {TASK_COLUMNS}
        from eg_tasks t
        where {where}
        order by t.created_at desc, t.id
        """,
        params,
    ).fetchall()
    return hydrate_tasks(conn, rows)


def create_task_in_workspace(conn, workspace_id: UUID, values: dict):
    """Cria tarefa vinculada diretamente ao workspace, sem exigir uma lista."""
    return conn.execute(
        f"""
        insert into eg_tasks (
          workspace_id, discipline, project_id, parent_task_id, title, description,
          status, group_status, priority, assignee_id, owner_id,
          start_date, due_date, recurrence, client_visible
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning {TASK_COLUMNS}
        """,
        (
            workspace_id,
            values.get("discipline"),
            values.get("project_id"),
            values.get("parent_task_id"),
            values["title"],
            values.get("description"),
            values["status"],
            values["group_status"],
            values.get("priority"),
            values.get("assignee_id"),
            values.get("owner_id"),
            values.get("start_date"),
            values.get("due_date"),
            values.get("recurrence") or "none",
            values.get("client_visible", True),
        ),
    ).fetchone()


def list_tasks(conn, list_id: UUID):
    rows = conn.execute(
        f"""
        select {TASK_COLUMNS}
        from eg_tasks
        where list_id = %s
        order by created_at desc, id
        """,
        (list_id,),
    ).fetchall()
    return hydrate_tasks(conn, rows)


def get_task(conn, task_id: UUID):
    row = conn.execute(
        f"select {TASK_COLUMNS} from eg_tasks where id = %s",
        (task_id,),
    ).fetchone()
    if not row:
        return None
    return hydrate_tasks(conn, [row])[0]


def hydrate_tasks(conn, rows: Iterable):
    task_rows = [dict(row) for row in rows]
    if not task_rows:
        return []
    task_ids = [row["id"] for row in task_rows]
    custom_fields: dict[UUID, list[dict]] = {}
    for row in conn.execute(
        "select id, task_id, field_name, field_value from eg_task_custom_fields where task_id = any(%s)",
        (task_ids,),
    ).fetchall():
        custom_fields.setdefault(row["task_id"], []).append(dict(row))
    dependencies: dict[UUID, list[dict]] = {}
    for row in conn.execute(
        "select id, task_id, depends_on_task_id, type from eg_task_dependencies where task_id = any(%s)",
        (task_ids,),
    ).fetchall():
        dependencies.setdefault(row["task_id"], []).append(dict(row))
    subtasks: dict[UUID, list[dict]] = {}
    for row in conn.execute(
        """
        select id, task_id, title, is_completed, created_at, updated_at
        from eg_task_subtasks where task_id = any(%s)
        order by created_at, id
        """,
        (task_ids,),
    ).fetchall():
        subtasks.setdefault(row["task_id"], []).append(dict(row))
    for task in task_rows:
        task_id = task["id"]
        task["custom_fields"] = custom_fields.get(task_id, [])
        task["dependencies"] = dependencies.get(task_id, [])
        task["subtasks"] = subtasks.get(task_id, [])
    return task_rows


def user_can_belong_to_workspace(conn, workspace_id: UUID, user_id: UUID) -> bool:
    row = conn.execute(
        """
        select exists (
          select 1
          from workspaces w
          join users u on u.id = %s and u.is_active = true
          where w.id = %s
            and w.status = 'active'
            and (
              workspace_access_role(w.id, u.id) is not null
              or exists (
                select 1 from memberships m
                join organizations o on o.id = m.organization_id
                where m.user_id = u.id
                  and m.role = 'eg_admin'
                  and o.id = w.tenant_organization_id
              )
            )
        ) as allowed
        """,
        (user_id, workspace_id),
    ).fetchone()
    return bool(row and row["allowed"])


def project_belongs_to_workspace(conn, workspace_id: UUID, project_id: UUID) -> bool:
    """Impede vincular a tarefa a um projeto de outro cliente."""
    return conn.execute(
        "select 1 from projects where id = %s and workspace_id = %s",
        (project_id, workspace_id),
    ).fetchone() is not None


def parent_would_cycle(conn, task_id: UUID, parent_id: UUID) -> bool:
    """Subir a cadeia de pais para não criar ciclo (A pai de B, B pai de A)."""
    seen: set[UUID] = set()
    current = parent_id
    while current is not None:
        if current == task_id:
            return True
        if current in seen:
            return True
        seen.add(current)
        row = conn.execute("select parent_task_id from eg_tasks where id = %s", (current,)).fetchone()
        current = row["parent_task_id"] if row else None
    return False


def task_ids_in_workspace(conn, workspace_id: UUID, task_ids: list[UUID]) -> set[UUID]:
    """Aceita tanto tarefas novas (workspace_id direto) quanto legadas (via list_id)."""
    if not task_ids:
        return set()
    rows = conn.execute(
        """
        select t.id
        from eg_tasks t
        left join eg_task_lists l on l.id = t.list_id
        where (
          t.workspace_id = %s
          or l.workspace_id = %s
        ) and t.id = any(%s)
        """,
        (workspace_id, workspace_id, task_ids),
    ).fetchall()
    return {row["id"] for row in rows}


def dependency_would_cycle(conn, task_id: UUID, depends_on_task_id: UUID) -> bool:
    row = conn.execute(
        """
        with recursive dependency_chain(id) as (
          select %s::uuid
          union
          select d.depends_on_task_id
          from eg_task_dependencies d
          join dependency_chain chain on chain.id = d.task_id
        )
        select exists(select 1 from dependency_chain where id = %s) as cycle
        """,
        (depends_on_task_id, task_id),
    ).fetchone()
    return bool(row and row["cycle"])


def create_task(conn, list_id: UUID, values: dict):
    return conn.execute(
        f"""
        insert into eg_tasks (
          list_id, project_id, parent_task_id, title, description, status,
          group_status, priority, assignee_id, owner_id, start_date, due_date,
          recurrence, client_visible
        ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        returning {TASK_COLUMNS}
        """,
        (
            list_id,
            values.get("project_id"),
            values.get("parent_task_id"),
            values["title"],
            values.get("description"),
            values["status"],
            values["group_status"],
            values.get("priority"),
            values.get("assignee_id"),
            values.get("owner_id"),
            values.get("start_date"),
            values.get("due_date"),
            values.get("recurrence") or "none",
            values.get("client_visible", True),
        ),
    ).fetchone()


def update_task(conn, task_id: UUID, updates: dict):
    allowed = {
        "title", "description", "status", "group_status", "priority",
        "assignee_id", "owner_id", "start_date", "due_date", "recurrence",
        "project_id", "parent_task_id", "client_visible",
    }
    selected = [(field, value) for field, value in updates.items() if field in allowed]
    if not selected:
        return conn.execute(f"select {TASK_COLUMNS} from eg_tasks where id = %s", (task_id,)).fetchone()
    assignments = ", ".join(f"{field} = %s" for field, _ in selected)
    params = [value for _, value in selected] + [task_id]
    return conn.execute(
        f"""
        update eg_tasks set {assignments}, updated_at = now()
        where id = %s
        returning {TASK_COLUMNS}
        """,
        params,
    ).fetchone()


def replace_custom_fields(conn, task_id: UUID, fields: list[dict]) -> None:
    conn.execute("delete from eg_task_custom_fields where task_id = %s", (task_id,))
    for field in fields:
        conn.execute(
            "insert into eg_task_custom_fields (task_id, field_name, field_value) values (%s, %s, %s)",
            (task_id, field["field_name"], field["field_value"]),
        )


def replace_dependencies(conn, task_id: UUID, dependencies: list[dict]) -> None:
    conn.execute("delete from eg_task_dependencies where task_id = %s", (task_id,))
    for dependency in dependencies:
        conn.execute(
            """
            insert into eg_task_dependencies (task_id, depends_on_task_id, type)
            values (%s, %s, %s)
            """,
            (task_id, dependency["depends_on_task_id"], dependency.get("type") or "waiting_on"),
        )


def replace_subtasks(conn, task_id: UUID, subtasks: list[dict]) -> None:
    existing = {
        row["id"]
        for row in conn.execute("select id from eg_task_subtasks where task_id = %s", (task_id,)).fetchall()
    }
    supplied = {subtask["id"] for subtask in subtasks if subtask.get("id") is not None}
    if not supplied.issubset(existing):
        raise ValueError("invalid_subtask")
    if supplied:
        conn.execute(
            "delete from eg_task_subtasks where task_id = %s and not (id = any(%s))",
            (task_id, list(supplied)),
        )
    else:
        conn.execute("delete from eg_task_subtasks where task_id = %s", (task_id,))
    for subtask in subtasks:
        if subtask.get("id") is not None:
            conn.execute(
                """
                update eg_task_subtasks
                set title = %s, is_completed = %s, updated_at = now()
                where id = %s and task_id = %s
                """,
                (subtask["title"], subtask.get("is_completed", False), subtask["id"], task_id),
            )
        else:
            conn.execute(
                "insert into eg_task_subtasks (task_id, title, is_completed) values (%s, %s, %s)",
                (task_id, subtask["title"], subtask.get("is_completed", False)),
            )


def create_recurring_successor(conn, task: dict):
    # Suporta tarefas novas (workspace_id) e legadas (list_id)
    if task.get("workspace_id"):
        return conn.execute(
            """
            insert into eg_tasks (
              workspace_id, discipline, title, description, status, group_status, priority,
              assignee_id, owner_id, due_date, recurrence, recurrence_source_task_id
            ) values (%s, %s, %s, %s, 'pending', 'NOT_STARTED', %s, %s, %s, %s, %s, %s)
            on conflict (recurrence_source_task_id) where recurrence_source_task_id is not null do nothing
            returning id
            """,
            (
                task["workspace_id"], task.get("discipline"), task["title"], task.get("description"),
                task.get("priority"), task.get("assignee_id"), task.get("owner_id"),
                task.get("next_due_date"), task["recurrence"], task["id"],
            ),
        ).fetchone()
    return conn.execute(
        """
        insert into eg_tasks (
          list_id, title, description, status, group_status, priority,
          assignee_id, owner_id, due_date, recurrence, recurrence_source_task_id
        ) values (%s, %s, %s, 'pending', 'NOT_STARTED', %s, %s, %s, %s, %s, %s)
        on conflict (recurrence_source_task_id) where recurrence_source_task_id is not null do nothing
        returning id
        """,
        (
            task["list_id"], task["title"], task.get("description"), task.get("priority"),
            task.get("assignee_id"), task.get("owner_id"), task.get("next_due_date"),
            task["recurrence"], task["id"],
        ),
    ).fetchone()


def copy_recurring_children(conn, source_task_id: UUID, target_task_id: UUID) -> None:
    conn.execute(
        """
        insert into eg_task_custom_fields (task_id, field_name, field_value)
        select %s, field_name, field_value from eg_task_custom_fields where task_id = %s
        """,
        (target_task_id, source_task_id),
    )
    conn.execute(
        """
        insert into eg_task_subtasks (task_id, title, is_completed)
        select %s, title, false from eg_task_subtasks where task_id = %s
        """,
        (target_task_id, source_task_id),
    )


def delete_task(conn, task_id: UUID) -> bool:
    return conn.execute("delete from eg_tasks where id = %s returning id", (task_id,)).fetchone() is not None


def add_subtask(conn, task_id: UUID, title: str):
    return conn.execute(
        """
        insert into eg_task_subtasks (task_id, title, is_completed)
        values (%s, %s, false)
        returning id, task_id, title, is_completed, created_at, updated_at
        """,
        (task_id, title),
    ).fetchone()


def toggle_subtask(conn, subtask_id: UUID):
    return conn.execute(
        """
        update eg_task_subtasks
        set is_completed = not is_completed, updated_at = now()
        where id = %s
        returning id, task_id, title, is_completed, created_at, updated_at
        """,
        (subtask_id,),
    ).fetchone()


def delete_subtask(conn, subtask_id: UUID) -> bool:
    return conn.execute(
        "delete from eg_task_subtasks where id = %s returning id",
        (subtask_id,),
    ).fetchone() is not None


COMMENT_COLUMNS = """
  c.id, c.task_id, c.author_id, c.body, c.client_visible,
  c.created_at, c.updated_at, u.display_name as author_name
"""


def list_task_comments(conn, task_id: UUID, include_internal: bool):
    """Cliente só enxerga o que foi marcado como visível para ele."""
    if include_internal:
        return conn.execute(
            f"""
            select {COMMENT_COLUMNS}
            from eg_task_comments c
            left join users u on u.id = c.author_id
            where c.task_id = %s
            order by c.created_at asc
            """,
            (task_id,),
        ).fetchall()
    return conn.execute(
        f"""
        select {COMMENT_COLUMNS}
        from eg_task_comments c
        left join users u on u.id = c.author_id
        where c.task_id = %s and c.client_visible = true
        order by c.created_at asc
        """,
        (task_id,),
    ).fetchall()


def create_task_comment(conn, task_id: UUID, author_id: UUID, body: str, client_visible: bool):
    row = conn.execute(
        """
        insert into eg_task_comments (task_id, author_id, body, client_visible)
        values (%s, %s, %s, %s)
        returning id
        """,
        (task_id, author_id, body, client_visible),
    ).fetchone()
    return conn.execute(
        f"""
        select {COMMENT_COLUMNS}
        from eg_task_comments c
        left join users u on u.id = c.author_id
        where c.id = %s
        """,
        (row["id"],),
    ).fetchone()


def delete_task_comment(conn, comment_id: UUID, author_id: UUID, is_admin: bool) -> bool:
    """Só o autor apaga o próprio comentário; admin de plataforma apaga qualquer um."""
    if is_admin:
        return conn.execute(
            "delete from eg_task_comments where id = %s returning id",
            (comment_id,),
        ).fetchone() is not None
    return conn.execute(
        "delete from eg_task_comments where id = %s and author_id = %s returning id",
        (comment_id, author_id),
    ).fetchone() is not None


def find_comment_task(conn, comment_id: UUID):
    return conn.execute(
        "select task_id from eg_task_comments where id = %s",
        (comment_id,),
    ).fetchone()


def list_my_tasks(conn, user_id: UUID, is_admin: bool):
    """Tarefas atribuídas a mim (ou das quais sou dono) em todos os workspaces
    que posso acessar — incluindo o workspace interno da EG.

    Suporta tanto tarefas novas (com workspace_id direto) quanto tarefas legadas
    (vinculadas via eg_task_lists). O UNION garante que ambas apareçam no Cockpit.
    """
    return conn.execute(
        """
        select
          t.id, t.title, t.status, t.group_status, t.priority, t.due_date,
          t.project_id, t.parent_task_id,
          coalesce(l.id, null) as list_id,
          coalesce(l.name, 'Geral') as list_name,
          coalesce(l.type, t.discipline, 'growth') as list_type,
          w.id as workspace_id, w.name as workspace_name, w.kind as workspace_kind,
          p.name as project_name
        from eg_tasks t
        left join eg_task_lists l on l.id = t.list_id
        join workspaces w on (
          w.id = coalesce(t.workspace_id, l.workspace_id)
          and w.status = 'active'
        )
        left join projects p on p.id = t.project_id
        where (t.assignee_id = %s or t.owner_id = %s)
          and t.group_status <> 'CLOSED'
          and (%s or workspace_access_role(w.id, %s) is not null)
        order by t.due_date nulls last, t.updated_at desc
        limit 50
        """,
        (user_id, user_id, is_admin, user_id),
    ).fetchall()


def list_assignable_users(conn, workspace_id: UUID):
    """Usuários que podem ser responsável/dono de tarefa neste workspace.

    Espelha exatamente a regra de `user_can_belong_to_workspace`: quem tem papel
    no workspace, mais os eg_admin do tenant. Assim o seletor da UI nunca
    oferece alguém que o backend recusaria com 422.
    """
    return conn.execute(
        """
        select distinct u.id, u.display_name, u.email
        from users u
        join workspaces w on w.id = %s and w.status = 'active'
        where u.is_active = true
          and (
            workspace_access_role(w.id, u.id) is not null
            or exists (
              select 1 from memberships m
              join organizations o on o.id = m.organization_id
              where m.user_id = u.id
                and m.role = 'eg_admin'
                and o.id = w.tenant_organization_id
            )
          )
        order by u.display_name
        """,
        (workspace_id,),
    ).fetchall()
