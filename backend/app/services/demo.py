from sqlmodel import Session, delete, func, select

from app.models import Day, Persona
from scripts.seed import seed


def reset(session: Session) -> tuple[int, int]:
    """Drop every persona and day, then load the demo data again (undo live check-ins)."""
    session.exec(delete(Day))
    session.exec(delete(Persona))
    session.commit()
    seed(session)
    personas = session.exec(select(func.count()).select_from(Persona)).one()
    days = session.exec(select(func.count()).select_from(Day)).one()
    return personas, days
