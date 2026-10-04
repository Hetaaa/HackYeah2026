from fastapi import APIRouter

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import PredictionRead, TodayRead
from app.services import predictions as predictions_service
from app.services import today as today_service

router = APIRouter(prefix="/users/{user_id}/today", tags=["today"], responses=NOT_FOUND)


@router.get(
    "/prediction",
    response_model=PredictionRead,
    summary="Personalized pre-survey wellness prediction",
)
def get_prediction(persona: PersonaDep, session: SessionDep) -> PredictionRead:
    return predictions_service.get_prediction(session, persona)


@router.get(
    "",
    summary="Today (home screen)",
    description="What last night and yesterday already say about today, based on the persona's "
    "significant patterns, plus today's check-in once filled. Demo personas use their demo "
    "clock (`PersonaRead.today`).",
)
def get_today(persona: PersonaDep, session: SessionDep) -> TodayRead:
    return today_service.get_today(session, persona)
