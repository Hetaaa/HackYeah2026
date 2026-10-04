import datetime as dt

from sqlmodel import Session

from app import analysis
from app.models import Day
from app.schemas import SurveyCreate, SurveyRead
from app.services.days import get_analysis, get_day, survey_of


def get_survey(session: Session, user_id: str, date: dt.date) -> SurveyRead | None:
    day = get_day(session, user_id, date)
    if day is None or survey_of(day) is None:
        return None
    return to_read(session, day)


def save_survey(session: Session, user_id: str, date: dt.date, data: SurveyCreate) -> SurveyRead:
    day = get_day(session, user_id, date)
    answers = data.model_dump()
    if day is None or day.survey_at is None:
        # first fill only: editing an old survey must not move its time past that night's sleep
        answers["survey_at"] = dt.datetime.now(dt.UTC)
    if day is None:
        day = Day.model_validate({"user_id": user_id, "date": date, **answers})
    else:
        day.sqlmodel_update(answers)
    session.add(day)
    session.commit()
    session.refresh(day)
    return to_read(session, day)


def delete_survey(session: Session, user_id: str, date: dt.date) -> bool:
    """Clears the day's answers (watch data stays). False when there was no survey."""
    day = get_day(session, user_id, date)
    if day is None or survey_of(day) is None:
        return False
    day.sqlmodel_update(
        {"mood": None, "fatigue": None, "sleep_quality": None, "stress": None, "survey_at": None}
    )
    session.add(day)
    session.commit()
    return True


def to_read(session: Session, day: Day) -> SurveyRead:
    """The label is personal (relative to the user's history), so it needs all their days."""
    return read_from(day, get_analysis(session, day.user_id))


def read_from(day: Day, result: dict) -> SurveyRead:
    return SurveyRead(
        date=day.date,
        mood=day.mood,
        fatigue=day.fatigue,
        sleep_quality=day.sleep_quality,
        stress=day.stress,
        label=analysis.label_day(result, day.date),
        score=analysis.score_day(result, day.date),
    )
