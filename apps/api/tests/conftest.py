"""Fixtures dos testes unitários da API.

Escopo: testes puros, sem banco. Constroem `CurrentUserResponse` na mão para
exercitar a política de acesso e as funções de derivação sem tocar Postgres —
o que os `smoke_*.py` não cobrem de forma barata.
"""

from pathlib import Path
import sys
from uuid import UUID, uuid4

import pytest

# Permite `import bioma_api...` rodando `pytest` de apps/api sem instalar o pacote.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bioma_api.domain.models import Role  # noqa: E402
from bioma_api.schemas.auth import CurrentUserResponse, OrganizationSummary  # noqa: E402

# Slug reservado que `is_platform_admin` reconhece como control plane da EG.
EG_ORG_ID = UUID("00000000-0000-0000-0000-0000000000e9")


def make_user(*organizations: OrganizationSummary) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=uuid4(),
        email="user@example.com",
        display_name="Teste",
        organizations=list(organizations),
    )


@pytest.fixture
def eg_admin() -> CurrentUserResponse:
    return make_user(
        OrganizationSummary(id=EG_ORG_ID, name="EverGreen", slug="eg", role=Role.eg_admin)
    )


@pytest.fixture
def client_user_factory():
    """Cria um `client_user` de uma organização de cliente com módulos dados."""

    def _make(org_id: UUID | None = None, enabled_modules: list[str] | None = None):
        return make_user(
            OrganizationSummary(
                id=org_id or uuid4(),
                name="Cliente",
                slug="cliente",
                role=Role.client_user,
                enabled_modules=enabled_modules or ["hub", "content", "files"],
            )
        )

    return _make
