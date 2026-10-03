from sqlmodel import Session

from app import analysis
from app.models import Day, Persona
from app.schemas import TodayRead
from app.services import surveys as surveys_service
from app.services import users as users_service
from app.services.days import list_days, survey_of

SURVEY_FIELDS = {"mood": None, "fatigue": None, "sleep_quality": None, "stress": None}


def get_today(session: Session, persona: Persona) -> TodayRead:
    """Heads-up / good signs come from a "morning" analysis without today's check-in, so they
    stay the same after the user checks in; summary and survey come from the current data."""
    today = users_service.today_of(persona)
    days = list_days(session, persona.id)
    current = analysis.analyze(days, persona.analysis_window_end)
    row = next((d for d in days if d.date == today), None)
    # today without its answers (and an empty row if the watch hasn't synced today yet, so the
    # day-before activity can still trigger a signal)
    morning_row = Day.model_validate(
        (row.model_dump() if row else {"user_id": persona.id, "date": today})
        | SURVEY_FIELDS
        | {"survey_at": None}
    )
    morning_days = [d for d in days if d.date != today] + [morning_row]
    morning = analysis.analyze(morning_days, persona.analysis_window_end)
    survey = surveys_service.read_from(row, current) if row and survey_of(row) else None
    return analysis.today(current, morning, today, survey)
