from uuid import UUID

from fastapi import HTTPException, status

from bioma_api.access import is_platform_admin, require_workspace_capability
from bioma_api.crypto import decrypt_secret, encrypt_secret, require_encryption_configured
from bioma_api.db import connect
from bioma_api.repositories import vault as vault_repo
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.vault import (
    VaultCopyRequest,
    VaultCopyResponse,
    VaultCredentialCreate,
    VaultCredentialSummary,
    VaultCredentialUpdate,
    VaultReasonRequest,
    VaultRevealResponse,
    VaultStatusUpdate,
    VaultSecrets,
)


SECRET_COLUMNS = {
    "username": "encrypted_username",
    "email": "encrypted_email",
    "password": "encrypted_password",
    "other_access": "encrypted_other_access",
    "token": "encrypted_token",
    "recovery_codes": "encrypted_recovery_codes",
    "notes": "encrypted_notes",
}
BLOCKED_STATUSES = {"compromised", "revoked"}


def list_credentials(workspace_id: UUID, user: CurrentUserResponse) -> list[VaultCredentialSummary]:
    with connect() as conn:
        context = _workspace_context(conn, workspace_id, user, "view")
        rows = vault_repo.list_credentials(
            conn,
            context["workspace_id"],
            include_internal=context["access_role"] != "client_user",
        )
    return [VaultCredentialSummary(**row) for row in rows]


def create_credential(
    workspace_id: UUID,
    payload: VaultCredentialCreate,
    user: CurrentUserResponse,
) -> VaultCredentialSummary:
    require_encryption_configured()
    with connect() as conn:
        context = _workspace_context(conn, workspace_id, user)
        role = context["access_role"]
        capability = "submit_secrets" if role == "client_user" else "manage_secrets"
        require_workspace_capability(context, user, capability)
        data = payload.model_dump()
        data["visibility"] = "client" if role == "client_user" else data["visibility"]
        if role == "client_user":
            data["owner_user_id"] = user.id
        _validate_owner(conn, context, data.get("owner_user_id"))
        data.update(_encrypted_secrets(data.pop("secrets")))
        row = vault_repo.create_credential(conn, context, user.id, data)
        vault_repo.write_audit(
            conn,
            user.id,
            context["subject_organization_id"],
            "vault.credential_created",
            {
                "workspace_id": str(context["workspace_id"]),
                "credential_id": str(row["id"]),
                "platform": row["platform"],
                "visibility": row["visibility"],
            },
        )
    return VaultCredentialSummary(**row)


def update_credential(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultCredentialUpdate,
    user: CurrentUserResponse,
) -> VaultCredentialSummary:
    with connect() as conn:
        context = _workspace_context(conn, workspace_id, user, "manage_secrets")
        current = _credential(conn, context, credential_id)
        data = payload.model_dump(exclude_unset=True)
        _validate_owner(conn, context, data.get("owner_user_id"))
        secrets = data.pop("secrets", None)
        if secrets is not None:
            require_encryption_configured()
            data.update(_encrypted_secrets(secrets))
        row = vault_repo.update_credential(conn, context["workspace_id"], credential_id, user.id, data)
        vault_repo.write_audit(
            conn,
            user.id,
            context["subject_organization_id"],
            "vault.credential_updated",
            {
                "workspace_id": str(context["workspace_id"]),
                "credential_id": str(credential_id),
                "rotated": secrets is not None,
                "previous_version": current["version"],
                "version": row["version"],
            },
        )
    return _summary_for(conn_row=row)


def set_status(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultStatusUpdate,
    user: CurrentUserResponse,
) -> VaultCredentialSummary:
    with connect() as conn:
        context = _workspace_context(conn, workspace_id, user, "manage_secrets")
        current = _credential(conn, context, credential_id)
        row = vault_repo.update_status(conn, context["workspace_id"], credential_id, user.id, payload.status)
        vault_repo.write_audit(
            conn,
            user.id,
            context["subject_organization_id"],
            "vault.credential_status_changed",
            {
                "workspace_id": str(context["workspace_id"]),
                "credential_id": str(credential_id),
                "from": current["status"],
                "to": payload.status,
            },
        )
    return _summary_for(conn_row=row)


def reveal_credential(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultReasonRequest,
    user: CurrentUserResponse,
) -> VaultRevealResponse:
    require_encryption_configured()
    with connect() as conn:
        context = _workspace_context(conn, workspace_id, user, "reveal_secrets")
        row = _credential(conn, context, credential_id)
        _assert_revealable(row)
        vault_repo.write_audit(
            conn,
            user.id,
            context["subject_organization_id"],
            "vault.credential_revealed",
            {
                "workspace_id": str(context["workspace_id"]),
                "credential_id": str(credential_id),
                "reason": payload.reason,
            },
        )
        secrets = _decrypted_secrets(row)
    return VaultRevealResponse(credential_id=credential_id, secrets=VaultSecrets(**secrets))


def copy_secret(
    workspace_id: UUID,
    credential_id: UUID,
    payload: VaultCopyRequest,
    user: CurrentUserResponse,
) -> VaultCopyResponse:
    require_encryption_configured()
    with connect() as conn:
        context = _workspace_context(conn, workspace_id, user, "reveal_secrets")
        row = _credential(conn, context, credential_id)
        _assert_revealable(row)
        encrypted_value = row[SECRET_COLUMNS[payload.field]]
        if not encrypted_value:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campo de acesso não cadastrado.")
        vault_repo.write_audit(
            conn,
            user.id,
            context["subject_organization_id"],
            "vault.credential_copied",
            {
                "workspace_id": str(context["workspace_id"]),
                "credential_id": str(credential_id),
                "field": payload.field,
                "reason": payload.reason,
            },
        )
        value = decrypt_secret(encrypted_value)
    return VaultCopyResponse(credential_id=credential_id, field=payload.field, value=value or "")


def _workspace_context(conn, workspace_id: UUID, user: CurrentUserResponse, capability: str | None = None):
    context = vault_repo.find_workspace_context(conn, workspace_id, is_platform_admin(user), user.id)
    if not context:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace não encontrado.")
    if capability:
        require_workspace_capability(context, user, capability)
    return context


def _credential(conn, context, credential_id: UUID):
    row = vault_repo.find_credential(conn, context["workspace_id"], credential_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acesso não encontrado.")
    return row


def _assert_revealable(row) -> None:
    if row["status"] in BLOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acesso comprometido ou revogado não pode ser revelado.",
        )


def _validate_owner(conn, context, owner_user_id: UUID | None) -> None:
    if owner_user_id and not vault_repo.user_belongs_to_workspace(conn, context["workspace_id"], owner_user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Responsável precisa pertencer ao mesmo workspace.",
        )


def _encrypted_secrets(secrets: dict) -> dict[str, str | None]:
    return {
        column: encrypt_secret(value) if value else None
        for field, column in SECRET_COLUMNS.items()
        if (value := secrets.get(field)) is not None
    }


def _decrypted_secrets(row) -> dict[str, str | None]:
    return {
        field: decrypt_secret(row[column])
        for field, column in SECRET_COLUMNS.items()
        if row[column] is not None
    }


def _summary_for(conn_row) -> VaultCredentialSummary:
    return VaultCredentialSummary(
        id=conn_row["id"],
        workspace_id=conn_row["workspace_id"],
        platform=conn_row["platform"],
        label=conn_row["label"],
        account_hint=conn_row["account_hint"],
        visibility=conn_row["visibility"],
        status=conn_row["status"],
        expires_at=conn_row["expires_at"],
        owner_user_id=conn_row["owner_user_id"],
        owner_name=None,
        version=conn_row["version"],
        last_rotated_at=conn_row["last_rotated_at"],
        created_at=conn_row["created_at"],
        updated_at=conn_row["updated_at"],
    )
