"""Portais sem login por cliente: painel de dados reais (público) e operação EG.

O painel devolve só agregados. As rotas `/eg` exigem a chave do portal no cabeçalho
`Authorization: Portal <chave>` (o CORS da API já libera `Authorization`).
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request
from pydantic import BaseModel, Field

from bioma_api.schemas.kommo import KommoDashboardResponse
from bioma_api.services import kommo_portal

router = APIRouter(prefix="/portal-api/{slug}", tags=["portal"])


def admin_key(authorization: str | None = Header(default=None)) -> None:
    kommo_portal.require_admin_key(authorization)


class PortalKommoConnectInput(BaseModel):
    subdomain: str
    access_token: str


class PortalBatchInput(BaseModel):
    limit: int = Field(default=10, ge=1, le=40)


class PortalClassifyInput(PortalBatchInput):
    write: bool = True


class PortalClassifyTestInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    phone: str | None = None


@router.get("/kommo/dashboard", response_model=KommoDashboardResponse)
def portal_dashboard(slug: str, days: int = Query(default=0)) -> KommoDashboardResponse:
    """Painel de dados reais: agregados da última sincronização, sem dado pessoal."""
    return KommoDashboardResponse(**kommo_portal.public_dashboard(slug, days))


@router.post("/kommo/webhook/{secret}")
async def portal_kommo_webhook(slug: str, secret: str, request: Request, background: BackgroundTasks) -> dict:
    """Destino do webhook do Kommo. Responde na hora e classifica em segundo plano."""
    organization_id = kommo_portal.webhook_authorize(slug, secret)
    form = {key: str(value) for key, value in (await request.form()).items()}
    background.add_task(kommo_portal.webhook_process, organization_id, kommo_portal.webhook_lead_ids(form))
    return {"status": "ok"}


@router.get("/eg/status", dependencies=[Depends(admin_key)])
def portal_eg_status(slug: str) -> dict:
    return kommo_portal.eg_status(slug)


@router.post("/eg/kommo/connect", dependencies=[Depends(admin_key)])
def portal_eg_connect(slug: str, payload: PortalKommoConnectInput) -> dict:
    return kommo_portal.connect_kommo(slug, payload.subdomain, payload.access_token)


@router.post("/eg/kommo/sync", response_model=KommoDashboardResponse, dependencies=[Depends(admin_key)])
def portal_eg_sync(slug: str, days: int = Query(default=0)) -> KommoDashboardResponse:
    return KommoDashboardResponse(**kommo_portal.sync(slug, days))


@router.get("/eg/kommo/debug", dependencies=[Depends(admin_key)])
def portal_eg_kommo_debug(slug: str) -> dict:
    return kommo_portal.debug_kommo(slug)


@router.get("/eg/dedup/runs", dependencies=[Depends(admin_key)])
def portal_eg_dedup_runs(slug: str) -> list[dict]:
    return kommo_portal.dedup_runs(slug)


@router.post("/eg/dedup/runs", dependencies=[Depends(admin_key)])
def portal_eg_dedup_simulate(slug: str) -> dict:
    return kommo_portal.dedup_simulate(slug)


@router.get("/eg/dedup/runs/{run_id}", dependencies=[Depends(admin_key)])
def portal_eg_dedup_run(
    slug: str,
    run_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    only_pending: bool = Query(default=False),
) -> dict:
    return kommo_portal.dedup_run_detail(slug, run_id, page, page_size, only_pending)


@router.post("/eg/dedup/runs/{run_id}/apply", dependencies=[Depends(admin_key)])
def portal_eg_dedup_apply(slug: str, run_id: UUID, payload: PortalBatchInput) -> dict:
    """Unifica o próximo lote de grupos no Kommo: move os leads e marca a duplicata."""
    return kommo_portal.dedup_apply(slug, run_id, payload.limit)


@router.post("/eg/classification/batch", dependencies=[Depends(admin_key)])
def portal_eg_classify_batch(slug: str, payload: PortalClassifyInput) -> dict:
    """Classifica o próximo lote de leads pela conversa e grava os campos vazios no Kommo."""
    return kommo_portal.classify_batch(slug, payload.limit, payload.write)


@router.get("/eg/classification/results", dependencies=[Depends(admin_key)])
def portal_eg_classification_results(
    slug: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return kommo_portal.classification_results(slug, page, page_size)


@router.post("/eg/classification/test", dependencies=[Depends(admin_key)])
def portal_eg_classify_test(slug: str, payload: PortalClassifyTestInput) -> dict:
    """Testa a classificação de uma mensagem sob demanda com Laya AI e regras sem alterar o CRM."""
    return kommo_portal.test_classification(slug, payload.text, payload.phone)


@router.post("/eg/webhook", dependencies=[Depends(admin_key)])
def portal_eg_webhook_enable(slug: str, request: Request) -> dict:
    """Registra no Kommo o webhook de mensagem e lead novos apontando para esta API."""
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return kommo_portal.webhook_enable(slug, f"{forwarded_proto}://{host}")


@router.post("/eg/classification/reset", dependencies=[Depends(admin_key)])
def portal_eg_classification_reset(slug: str) -> dict:
    """Limpa o histórico de classificações de teste para permitir início limpo."""
    return kommo_portal.classification_reset(slug)


@router.post("/eg/classification/leads/{lead_id}/apply", dependencies=[Depends(admin_key)])
def portal_eg_classification_apply_lead(slug: str, lead_id: int) -> dict:
    """Aprova e envia as decisões de um lead sugerido diretamente ao Kommo."""
    return kommo_portal.apply_classification(slug, lead_id)


@router.post("/eg/classification/apply-batch", dependencies=[Depends(admin_key)])
def portal_eg_classification_apply_batch(slug: str, payload: PortalBatchInput) -> dict:
    """Aprova e envia as decisões de leads sugeridos em lote para o Kommo."""
    return kommo_portal.apply_classification_batch(slug, payload.limit)

