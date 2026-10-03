from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.db import SessionDep
from app.schemas import DemoReset
from app.services import demo as demo_service

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post(
    "/reset",
    summary="Reset demo data",
    description="Restores the seeded personas and days (undoes check-ins made during a demo). "
    "Disabled when ENV=prod.",
)
def reset_demo(session: SessionDep) -> DemoReset:
    if settings.env == "prod":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Demo reset is disabled in prod")
    personas, days = demo_service.reset(session)
    return DemoReset(personas=personas, days=days)
