import datetime as dt

from sqlmodel import Session, select

from app import analysis
from app.models import Day, Persona, SurveyBase
from app.schemas import DayDetail, DaySummary


def list_days(session: Session, user_id: str) -> list[Day]:
    return list(session.exec(select(Day).where(Day.user_id == user_id).order_by(Day.date)).all())


def get_day(session: Session, user_id: str, date: dt.date) -> Day | None:
    return session.exec(select(Day).where(Day.user_id == user_id, Day.date == date)).first()


def analyze_user(session: Session, user_id: str) -> dict:
    """Analysis of all days of one user (cached in app.analysis until the data changes)."""
    persona = session.get(Persona, user_id)
    window_end = persona.analysis_window_end if persona else None
    return analysis.analyze(list_days(session, user_id), window_end)


def list_day_summaries(
    session: Session, user_id: str, date_from: dt.date | None, date_to: dt.date | None
) -> list[DaySummary]:
    result = analyze_user(session, user_id)
    return [
        analysis.day_summary(result, day.date)
        for day in list_days(session, user_id)
        if (date_from is None or day.date >= date_from) and (date_to is None or day.date <= date_to)
    ]


def get_day_detail(session: Session, user_id: str, date: dt.date) -> DayDetail | None:
    day = get_day(session, user_id, date)
    if day is None:
        return None
    return analysis.day_detail(analyze_user(session, user_id), day, survey_of(day))


def survey_of(day: Day) -> SurveyBase | None:
    if None in (day.mood, day.fatigue, day.sleep_quality, day.stress):
        return None
    return SurveyBase.model_validate(day, from_attributes=True)
