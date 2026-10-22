from typing import Any
from uuid import UUID
from psycopg.types.json import Jsonb


def list_validations(conn, workspace_id: UUID) -> list[dict]:
    return conn.execute(
        """
        select
            id, workspace_id, tenant_organization_id, title, product_or_service,
            target_audience, current_price_cents, status, value_equation, value_score,
            problems_and_solutions, offer_stack, board_verdict, created_by,
            created_at, updated_at
        from workspace_offer_validations
        where workspace_id = %s
        order by created_at desc
        """,
        (workspace_id,),
    ).fetchall()


def get_validation(conn, validation_id: UUID, workspace_id: UUID):
    return conn.execute(
        """
        select
            id, workspace_id, tenant_organization_id, title, product_or_service,
            target_audience, current_price_cents, status, value_equation, value_score,
            problems_and_solutions, offer_stack, board_verdict, created_by,
            created_at, updated_at
        from workspace_offer_validations
        where id = %s and workspace_id = %s
        """,
        (validation_id, workspace_id),
    ).fetchone()


def create_validation(
    conn,
    workspace_id: UUID,
    tenant_organization_id: UUID,
    user_id: UUID,
    title: str,
    product_or_service: str,
    target_audience: str,
    current_price_cents: int,
    status: str,
    value_equation: dict,
    value_score: float,
    problems_and_solutions: list,
    offer_stack: dict,
    board_verdict: dict,
) -> dict:
    return conn.execute(
        """
        insert into workspace_offer_validations (
            workspace_id,
            tenant_organization_id,
            created_by,
            title,
            product_or_service,
            target_audience,
            current_price_cents,
            status,
            value_equation,
            value_score,
            problems_and_solutions,
            offer_stack,
            board_verdict
        ) values (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        returning *
        """,
        (
            workspace_id,
            tenant_organization_id,
            user_id,
            title,
            product_or_service,
            target_audience,
            current_price_cents,
            status,
            Jsonb(value_equation),
            value_score,
            Jsonb(problems_and_solutions),
            Jsonb(offer_stack),
            Jsonb(board_verdict),
        ),
    ).fetchone()


def update_validation(
    conn,
    validation_id: UUID,
    workspace_id: UUID,
    title: str,
    product_or_service: str,
    target_audience: str,
    current_price_cents: int,
    status: str,
    value_equation: dict,
    value_score: float,
    problems_and_solutions: list,
    offer_stack: dict,
    board_verdict: dict,
) -> dict:
    return conn.execute(
        """
        update workspace_offer_validations set
            title = %s,
            product_or_service = %s,
            target_audience = %s,
            current_price_cents = %s,
            status = %s,
            value_equation = %s,
            value_score = %s,
            problems_and_solutions = %s,
            offer_stack = %s,
            board_verdict = %s,
            updated_at = now()
        where id = %s and workspace_id = %s
        returning *
        """,
        (
            title,
            product_or_service,
            target_audience,
            current_price_cents,
            status,
            Jsonb(value_equation),
            value_score,
            Jsonb(problems_and_solutions),
            Jsonb(offer_stack),
            Jsonb(board_verdict),
            validation_id,
            workspace_id,
        ),
    ).fetchone()


def delete_validation(conn, validation_id: UUID, workspace_id: UUID) -> bool:
    res = conn.execute(
        """
        delete from workspace_offer_validations
        where id = %s and workspace_id = %s
        returning id
        """,
        (validation_id, workspace_id),
    ).fetchone()
    return bool(res)
