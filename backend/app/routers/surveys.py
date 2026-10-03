import datetime as dt

from fastapi import APIRouter, HTTPException, status

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import SurveyCreate, SurveyRead
from app.services import surveys as surveys_service

router = APIRouter(prefix="/users/{user_id}/surveys", tags=["surveys"], responses=NOT_FOUND)


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
    description="Creates or overwrites the answers (1-5) and returns the computed day label.",
)
def save_survey(
    persona: PersonaDep, date: dt.date, data: SurveyCreate, session: SessionDep
) -> SurveyRead:
    return surveys_service.save_survey(session, persona.id, date, data)
