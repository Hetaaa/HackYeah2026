from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.db import SessionDep
from app.schemas import DemoReset, ErrorRead
from app.services import demo as demo_service

router = APIRouter(prefix="/demo", tags=["demo"])
FORBIDDEN: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"model": ErrorRead, "description": "DEMO_RESET is not enabled"}
}


@router.post(
    "/reset",
    summary="Reset demo data",
    description="Restores the demo personas and their days (undoes check-ins made during a "
    "demo); other users are kept. Enabled only with DEMO_RESET=true.",
    responses=FORBIDDEN,
)
def reset_demo(session: SessionDep) -> DemoReset:
    if not settings.demo_reset:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Demo reset is disabled")
    personas, days = demo_service.reset(session)
    return DemoReset(personas=personas, days=days)
