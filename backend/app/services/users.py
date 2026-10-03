import datetime as dt
import uuid
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlmodel import Session, func, select

from app import analysis
from app.insights import config as C
from app.models import Day, Persona, SurveyBase
from app.schemas import PersonaCreate, PersonaRead
from app.services.days import get_analysis


def list_personas(session: Session) -> list[PersonaRead]:
    personas = session.exec(select(Persona).order_by(Persona.position, Persona.id)).all()
    return [to_read(session, persona) for persona in personas]


def create_persona(session: Session, data: PersonaCreate) -> Persona:
    """New users get a random id and are listed after the demo personas."""
    last = session.exec(select(func.max(Persona.position))).one()
    persona = Persona.model_validate(
        data.model_dump() | {"id": f"u{uuid.uuid4().hex[:12]}", "position": (last or 0) + 1}
    )
    session.add(persona)
    session.commit()
    session.refresh(persona)
    return persona


def get_persona(session: Session, user_id: str) -> Persona | None:
    return session.get(Persona, user_id)


def today_of(persona: Persona) -> dt.date:
    """Demo clock for recorded personas, the user's local date for everyone else."""
    return persona.demo_today or dt.datetime.now(ZoneInfo(C.TZ)).date()


def latest_survey_date(persona: Persona) -> dt.date:
    """Demo personas: their today. Real users: tomorrow (clock skew / time zones ahead)."""
    return persona.demo_today or today_of(persona) + dt.timedelta(days=1)


def demo_answers(persona: Persona) -> SurveyBase | None:
    """'mood,fatigue,sleep_quality,stress' -> SurveyBase; malformed values are ignored."""
    try:
        mood, fatigue, sleep_quality, stress = (int(v) for v in persona.demo_answers.split(","))
        return SurveyBase.model_validate(
            {"mood": mood, "fatigue": fatigue, "sleep_quality": sleep_quality, "stress": stress}
        )
    except (AttributeError, ValueError, ValidationError):
        return None


def to_read(session: Session, persona: Persona) -> PersonaRead:
    first_date, last_date, days_count = session.exec(
        select(func.min(Day.date), func.max(Day.date), func.count(Day.id)).where(
            Day.user_id == persona.id
        )
    ).one()
    result = get_analysis(session, persona.id)
    have, needed = analysis.days_with_data(result)
    return PersonaRead(
        id=persona.id,
        name=persona.name,
        description=persona.description,
        first_date=first_date,
        last_date=last_date,
        days_count=days_count,
        insights_status=analysis.insights_status(result),
        days_with_data=have,
        days_needed=needed,
        label_mode=analysis.label_mode(result),
        norm_reference=analysis.norm_reference(result),
        today=today_of(persona),
        is_demo=persona.demo_today is not None,
        demo_answers=demo_answers(persona),
        pattern_features=analysis.pattern_features(result),
    )


def delete_persona(session: Session, persona: Persona) -> None:
    for day in session.exec(select(Day).where(Day.user_id == persona.id)):
        session.delete(day)
    session.delete(persona)
    session.commit()
