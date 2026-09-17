"""Política de acesso compartilhada (`bioma_api.access`).

Estas funções são o coração do isolamento multi-tenant e agora são a fonte
única após a deduplicação (os 4 services perderam suas cópias de
`_accessible_client`). Um teste que fixa o comportamento aqui protege contra
regressão em todos os domínios de uma vez.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from bioma_api.access import (
    WORKSPACE_CAPABILITIES,
    check_organization_access,
    is_platform_admin,
    require_client_module,
    require_platform_admin,
    require_workspace_capability,
)


class TestPlatformAdmin:
    def test_eg_admin_reconhecido(self, eg_admin):
        assert is_platform_admin(eg_admin) is True

    def test_client_user_nao_e_admin(self, client_user_factory):
        assert is_platform_admin(client_user_factory()) is False

    def test_eg_admin_com_slug_errado_nao_e_admin(self, client_user_factory):
        # Papel eg_admin só vale no slug "eg"; noutra org não promove.
        from bioma_api.domain.models import Role
        from bioma_api.schemas.auth import OrganizationSummary
        from tests.conftest import make_user

        impostor = make_user(
            OrganizationSummary(id=uuid4(), name="Outra", slug="outra", role=Role.eg_admin)
        )
        assert is_platform_admin(impostor) is False

    def test_require_platform_admin_bloqueia_cliente(self, client_user_factory):
        with pytest.raises(HTTPException) as exc:
            require_platform_admin(client_user_factory())
        assert exc.value.status_code == 403


class TestOrganizationAccess:
    def test_admin_acessa_qualquer_org(self, eg_admin):
        # Não levanta: admin transita por qualquer organização.
        check_organization_access(eg_admin, uuid4())

    def test_membro_acessa_a_propria_org(self, client_user_factory):
        org_id = uuid4()
        user = client_user_factory(org_id=org_id)
        check_organization_access(user, org_id)

    def test_estranho_recebe_404_nao_403(self, client_user_factory):
        # 404 (não 403) para não confirmar a existência da org a quem não pertence.
        user = client_user_factory(org_id=uuid4())
        with pytest.raises(HTTPException) as exc:
            check_organization_access(user, uuid4())
        assert exc.value.status_code == 404

    def test_uuid_malformado_vira_422(self, eg_admin):
        with pytest.raises(HTTPException) as exc:
            check_organization_access(eg_admin, "não-é-uuid")
        assert exc.value.status_code == 422

    def test_papel_insuficiente_bloqueia(self, client_user_factory):
        org_id = uuid4()
        user = client_user_factory(org_id=org_id)
        with pytest.raises(HTTPException) as exc:
            check_organization_access(user, org_id, required_roles=["eg_admin"])
        assert exc.value.status_code == 404


class TestClientModuleGate:
    def test_admin_ignora_gate(self, eg_admin):
        require_client_module({"enabled_modules": []}, eg_admin, "analytics")

    def test_cliente_com_modulo_habilitado_passa(self, client_user_factory):
        user = client_user_factory(enabled_modules=["hub", "analytics"])
        require_client_module({"enabled_modules": ["hub", "analytics"]}, user, "analytics")

    def test_cliente_sem_modulo_recebe_403(self, client_user_factory):
        user = client_user_factory(enabled_modules=["hub"])
        with pytest.raises(HTTPException) as exc:
            require_client_module({"enabled_modules": ["hub"]}, user, "analytics")
        assert exc.value.status_code == 403

    def test_enabled_modules_ausente_bloqueia(self, client_user_factory):
        # Falta do campo não pode virar acesso liberado.
        user = client_user_factory()
        with pytest.raises(HTTPException):
            require_client_module({}, user, "analytics")


class TestWorkspaceCapabilityMatrix:
    def test_admin_tem_todas_as_capabilities(self, eg_admin):
        for capability in ("view", "manage_work", "approve", "reveal_secrets"):
            require_workspace_capability({"access_role": None}, eg_admin, capability)

    def test_viewer_so_ve(self, client_user_factory):
        user = client_user_factory()
        require_workspace_capability({"access_role": "viewer"}, user, "view")
        with pytest.raises(HTTPException) as exc:
            require_workspace_capability({"access_role": "viewer"}, user, "manage_work")
        assert exc.value.status_code == 403

    def test_client_user_nao_revela_segredo(self, client_user_factory):
        # Cliente deposita segredo (submit) mas nunca revela (reveal) — regra do vault.
        user = client_user_factory()
        require_workspace_capability({"access_role": "client_user"}, user, "submit_secrets")
        with pytest.raises(HTTPException):
            require_workspace_capability({"access_role": "client_user"}, user, "reveal_secrets")

    def test_papel_desconhecido_nega_tudo(self, client_user_factory):
        user = client_user_factory()
        with pytest.raises(HTTPException):
            require_workspace_capability({"access_role": "papel_inexistente"}, user, "view")

    def test_operator_nao_aprova(self, client_user_factory):
        # Separação de funções: quem opera não é quem aprova.
        user = client_user_factory()
        assert "approve" not in WORKSPACE_CAPABILITIES["operator"]
        with pytest.raises(HTTPException):
            require_workspace_capability({"access_role": "operator"}, user, "approve")

    def test_reveal_secrets_restrito_a_papeis_de_gestao(self):
        # reveal_secrets é o mais sensível: nenhum papel operacional/cliente o tem.
        for role in ("operator", "approver", "viewer", "client_user"):
            assert "reveal_secrets" not in WORKSPACE_CAPABILITIES[role]
        for role in ("platform_admin", "tenant_admin", "workspace_manager"):
            assert "reveal_secrets" in WORKSPACE_CAPABILITIES[role]
