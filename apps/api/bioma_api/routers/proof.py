from fastapi import APIRouter, Depends, Query

from bioma_api.auth import current_user_from_request
from bioma_api.schemas.auth import CurrentUserResponse
from bioma_api.schemas.proof import ProofPanel
from bioma_api.services import proof as service

router = APIRouter(prefix="/eg/proof", tags=["proof"])


@router.get("", response_model=ProofPanel)
def get_panel(
    weeks: int = Query(default=12, ge=1, le=52),
    user: CurrentUserResponse = Depends(current_user_from_request),
) -> ProofPanel:
    """Painel de prova: disponibilidade medida por fora, entregas e correções.

    Interno por enquanto (EG-only). Se um dia virar público, o que muda é o
    gate — os números já nascem com origem verificável.
    """
    return service.get_panel(user, weeks)
