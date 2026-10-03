from sqlmodel import Session

from app import analysis
from app.models import Persona
from app.schemas import TodayRead
from app.services import surveys as surveys_service
from app.services import users as users_service
from app.services.days import get_analysis, get_day


def get_today(session: Session, persona: Persona) -> TodayRead:
    today = users_service.today_of(persona)
    result = get_analysis(session, persona.id)
    day = get_day(session, persona.id, today)
    survey = surveys_service.get_survey(session, persona.id, today)
    return analysis.today(result, today, survey, has_row=day is not None)
