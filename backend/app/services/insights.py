from sqlmodel import Session

from app import analysis
from app.schemas import PatternReport, Recipe
from app.services.days import list_days


def get_patterns(session: Session, user_id: str) -> PatternReport:
    return analysis.bad_day_patterns(list_days(session, user_id))


def get_recipe(session: Session, user_id: str) -> Recipe:
    return analysis.good_day_recipe(list_days(session, user_id))
