"""Benchmark público + toggle administrativo.

- `public_router` (`/public/benchmark`): SEM autenticação. Serve apenas o
  agregado anonimizado consumido pelo site. Read-only.
- `admin_router` (`/benchmark/settings`): EG admin apenas. Lê e vira o toggle
  em_breve/ao_vivo — é aqui que o "Em Breve" do site é controlado, sem redeploy.
"""

from fastapi import APIRouter, Depends

from bioma_api.access import require_platform_admin
from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.benchmark import (
    BenchmarkPayload,
    BenchmarkSettingsResponse,
    BenchmarkSettingsUpdate,
)
from bioma_api.services import benchmark as benchmark_service

public_router = APIRouter(prefix="/public/benchmark", tags=["benchmark-public"])
admin_router = APIRouter(prefix="/benchmark", tags=["benchmark-admin"])


@public_router.get("", response_model=BenchmarkPayload)
def get_public_benchmark() -> BenchmarkPayload:
    return benchmark_service.get_public_benchmark()


@admin_router.get("/settings", response_model=BenchmarkSettingsResponse)
def get_settings(
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> BenchmarkSettingsResponse:
    require_platform_admin(user)
    return benchmark_service.get_settings_response()


@admin_router.patch("/settings", response_model=BenchmarkSettingsResponse)
def update_settings(
    payload: BenchmarkSettingsUpdate,
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> BenchmarkSettingsResponse:
    require_platform_admin(user)
    return benchmark_service.update_settings(payload)
