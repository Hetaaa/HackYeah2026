import datetime as dt

from sqlmodel import Session, func, select

from app import analysis
from app.models import Day, Persona, SurveyBase
from app.schemas import PersonaRead
from app.services.days import get_analysis


def list_personas(session: Session) -> list[PersonaRead]:
    personas = session.exec(select(Persona).order_by(Persona.position, Persona.id)).all()
    return [to_read(session, persona) for persona in personas]


def get_persona(session: Session, user_id: str) -> Persona | None:
    return session.get(Persona, user_id)


def today_of(persona: Persona) -> dt.date:
    """Demo clock for recorded personas, the real (UTC) date for everyone else."""
    return persona.demo_today or dt.datetime.now(dt.UTC).date()


def demo_answers(persona: Persona) -> SurveyBase | None:
    if not persona.demo_answers:
        return None
    mood, fatigue, sleep_quality, stress = (int(v) for v in persona.demo_answers.split(","))
    return SurveyBase(mood=mood, fatigue=fatigue, sleep_quality=sleep_quality, stress=stress)


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
    )
