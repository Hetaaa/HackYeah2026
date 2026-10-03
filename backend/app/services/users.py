from sqlmodel import Session, func, select

from app import analysis
from app.models import Day, Persona
from app.schemas import PersonaRead
from app.services.days import analyze_user


def list_personas(session: Session) -> list[PersonaRead]:
    personas = session.exec(select(Persona).order_by(Persona.id)).all()
    return [to_read(session, persona) for persona in personas]


def get_persona(session: Session, user_id: str) -> Persona | None:
    return session.get(Persona, user_id)


def to_read(session: Session, persona: Persona) -> PersonaRead:
    first_date, last_date, days_count = session.exec(
        select(func.min(Day.date), func.max(Day.date), func.count(Day.id)).where(
            Day.user_id == persona.id
        )
    ).one()
    result = analyze_user(session, persona.id)
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
    )
