from pathlib import Path
import os
import sys

from email_validator import EmailNotValidError, validate_email


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bioma_api.db import connect  # noqa: E402
from bioma_api.security import hash_password  # noqa: E402
from bioma_api.repositories import workspaces as workspaces_repo  # noqa: E402


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} não configurado.")
    return value


def main() -> None:
    try:
        email = validate_email(
            required_env("BOOTSTRAP_ADMIN_EMAIL"),
            check_deliverability=False,
        ).normalized
    except EmailNotValidError as exc:
        raise RuntimeError("BOOTSTRAP_ADMIN_EMAIL inválido.") from exc

    password = required_env("BOOTSTRAP_ADMIN_PASSWORD")
    if len(password) < 16:
        print(
            "AVISO: BOOTSTRAP_ADMIN_PASSWORD tem menos de 16 caracteres. "
            "O bootstrap continuará, mas use uma senha forte em produção."
        )

    display_name = os.getenv("BOOTSTRAP_ADMIN_DISPLAY_NAME", "Admin EG").strip() or "Admin EG"
    rotate_password = os.getenv("BOOTSTRAP_ROTATE_PASSWORD", "").lower() in {"1", "true", "yes"}

    with connect() as conn:
        organization = conn.execute(
            """
            insert into organizations (name, slug, type)
            values ('EverGreen', 'eg', 'eg')
            on conflict (slug) do update set name = excluded.name, updated_at = now()
            returning id
            """
        ).fetchone()
        workspaces_repo.provision_agency_workspace(conn, organization["id"], "Operação EG")

        user = conn.execute(
            "select id from users where lower(email) = %s",
            (email.lower(),),
        ).fetchone()
        if user:
            user_id = user["id"]
            if rotate_password:
                conn.execute(
                    """
                    update users
                    set display_name = %s, password_hash = %s, is_active = true, updated_at = now()
                    where id = %s
                    """,
                    (display_name, hash_password(password), user_id),
                )
            else:
                conn.execute(
                    "update users set display_name = %s, is_active = true, updated_at = now() where id = %s",
                    (display_name, user_id),
                )
        else:
            user_id = conn.execute(
                """
                insert into users (email, display_name, password_hash)
                values (%s, %s, %s)
                returning id
                """,
                (email, display_name, hash_password(password)),
            ).fetchone()["id"]

        conn.execute(
            """
            insert into memberships (user_id, organization_id, role)
            values (%s, %s, 'eg_admin')
            on conflict (user_id, organization_id) do update set role = excluded.role
            """,
            (user_id, organization["id"]),
        )

    print(f"bootstrap ok: {email}")


if __name__ == "__main__":
    main()
