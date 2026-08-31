from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from bioma_api.db import connect


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def readiness() -> dict[str, str]:
    try:
        with connect() as conn:
            conn.execute("select 1").fetchone()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível.",
        ) from exc

    return {
        "status": "ready",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
