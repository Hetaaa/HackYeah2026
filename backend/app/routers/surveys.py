import datetime as dt

from fastapi import APIRouter, HTTPException, status

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import SurveyCreate, SurveyRead
from app.services import surveys as surveys_service
from app.services import users as users_service

router = APIRouter(prefix="/users/{user_id}/surveys", tags=["surveys"], responses=NOT_FOUND)
EARLIEST_DATE = dt.date(2000, 1, 1)


@router.get(
    "/{date}",
    summary="Get the survey of a day",
    description="404 when the survey for this day is not filled yet.",
)
def get_survey(persona: PersonaDep, date: dt.date, session: SessionDep) -> SurveyRead:
    survey = surveys_service.get_survey(session, persona.id, date)
    if survey is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No survey for {date}")
    return survey


@router.put(
    "/{date}",
    summary="Save the survey of a day",
    description="Creates or overwrites the answers (1-5) and returns the computed day label. "
    "The date must be between 2000-01-01 and the persona's today (real users: tomorrow, UTC, "
    "for time zones ahead), otherwise 422.",
)
def save_survey(
    persona: PersonaDep, date: dt.date, data: SurveyCreate, session: SessionDep
) -> SurveyRead:
    if not EARLIEST_DATE <= date <= users_service.latest_survey_date(persona):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Date {date} is out of range"
        )
    return surveys_service.save_survey(session, persona.id, date, data)


@router.delete(
    "/{date}",
    summary="Delete the survey of a day",
    description="Clears the day's answers so the check-in can be filled again; watch data is "
    "kept. 404 when the day has no survey.",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_survey(persona: PersonaDep, date: dt.date, session: SessionDep) -> None:
    if not surveys_service.delete_survey(session, persona.id, date):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No survey for {date}")
