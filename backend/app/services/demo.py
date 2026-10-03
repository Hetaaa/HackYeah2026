from sqlmodel import Session, col, delete, func, select

from app.models import Day, Persona
from scripts.import_days import import_days, import_personas
from scripts.seed import DEMO_DIR


def reset(session: Session) -> tuple[int, int]:
    """Restore the demo personas from data/demo (undo live check-ins) in one transaction.

    Only demo personas (demo_today set) and their days are replaced; other users stay.
    """
    demo_ids = select(Persona.id).where(col(Persona.demo_today).is_not(None))
    session.exec(delete(Day).where(col(Day.user_id).in_(demo_ids)))
    session.exec(delete(Persona).where(col(Persona.demo_today).is_not(None)))
    import_personas(session, DEMO_DIR / "personas.csv", commit=False)
    import_days(session, DEMO_DIR / "days.csv", commit=False)
    session.commit()
    ids = select(Persona.id).where(col(Persona.demo_today).is_not(None))
    personas = session.exec(
        select(func.count()).select_from(Persona).where(col(Persona.id).in_(ids))
    ).one()
    days = session.exec(
        select(func.count()).select_from(Day).where(col(Day.user_id).in_(ids))
    ).one()
    return personas, days
