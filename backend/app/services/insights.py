from sqlmodel import Session

from app import analysis
from app.schemas import PatternChart, PatternReport, Recipe
from app.services.days import get_analysis


def get_patterns(session: Session, user_id: str) -> PatternReport:
    return analysis.bad_day_patterns(get_analysis(session, user_id))


def get_recipe(session: Session, user_id: str) -> Recipe:
    return analysis.good_day_recipe(get_analysis(session, user_id))


def get_pattern_chart(
    session: Session, user_id: str, feature: str, kind: str
) -> PatternChart | None:
    return analysis.pattern_chart(get_analysis(session, user_id), feature, kind)
