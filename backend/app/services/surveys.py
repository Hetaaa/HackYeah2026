import datetime as dt

from sqlmodel import Session

from app import analysis
from app.models import Day
from app.schemas import SurveyCreate, SurveyRead
from app.services.days import get_day, survey_of


def get_survey(session: Session, user_id: str, date: dt.date) -> SurveyRead | None:
    day = get_day(session, user_id, date)
    if day is None or survey_of(day) is None:
        return None
    return to_read(day)


def save_survey(session: Session, user_id: str, date: dt.date, data: SurveyCreate) -> SurveyRead:
    day = get_day(session, user_id, date)
    if day is None:
        day = Day.model_validate({"user_id": user_id, "date": date, **data.model_dump()})
    else:
        day.sqlmodel_update(data.model_dump())
    session.add(day)
    session.commit()
    session.refresh(day)
    return to_read(day)


def to_read(day: Day) -> SurveyRead:
    return SurveyRead(
        date=day.date,
        mood=day.mood,
        fatigue=day.fatigue,
        sleep_quality=day.sleep_quality,
        stress=day.stress,
        label=analysis.label_day(day),
        score=analysis.score_day(day),
    )
