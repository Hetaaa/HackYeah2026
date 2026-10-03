import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import DayDetail, DaySummary
from app.services import days as days_service

router = APIRouter(prefix="/users/{user_id}/days", tags=["days"], responses=NOT_FOUND)


@router.get(
    "",
    summary="Wellness calendar",
    description="Days with their label and up to 2 biggest deviations from the good-day norm.",
)
def list_days(
    persona: PersonaDep,
    session: SessionDep,
    date_from: Annotated[dt.date | None, Query(alias="from", examples=["2019-11-01"])] = None,
    date_to: Annotated[dt.date | None, Query(alias="to", examples=["2019-11-30"])] = None,
) -> list[DaySummary]:
    return days_service.list_day_summaries(session, persona.id, date_from, date_to)


@router.get(
    "/{date}",
    summary="Day details",
    description="All stats of the day against the personal norm, deviations and a summary.",
)
def get_day(persona: PersonaDep, date: dt.date, session: SessionDep) -> DayDetail:
    detail = days_service.get_day_detail(session, persona.id, date)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No data for {date}")
    return detail
