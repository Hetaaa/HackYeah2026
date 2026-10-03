import datetime as dt

from sqlmodel import Session, select

from app import analysis
from app.models import Day, SurveyBase
from app.schemas import DayDetail, DaySummary, FeatureValue


def list_days(session: Session, user_id: str) -> list[Day]:
    return list(session.exec(select(Day).where(Day.user_id == user_id).order_by(Day.date)).all())


def get_day(session: Session, user_id: str, date: dt.date) -> Day | None:
    return session.exec(select(Day).where(Day.user_id == user_id, Day.date == date)).first()


def list_day_summaries(
    session: Session, user_id: str, date_from: dt.date | None, date_to: dt.date | None
) -> list[DaySummary]:
    days = list_days(session, user_id)
    return [
        DaySummary(
            date=day.date,
            label=analysis.label_day(day),
            score=analysis.score_day(day),
            top_deviations=analysis.day_deviations(days, day.date)[:2],
        )
        for day in days
        if (date_from is None or day.date >= date_from) and (date_to is None or day.date <= date_to)
    ]


def get_day_detail(session: Session, user_id: str, date: dt.date) -> DayDetail | None:
    day = get_day(session, user_id, date)
    if day is None:
        return None
    days = list_days(session, user_id)
    norm = analysis.personal_norm(days)
    features = [
        FeatureValue(
            feature=feature,
            label=info.label,
            unit=info.unit,
            value=getattr(day, feature),
            norm=norm.get(feature),
        )
        for feature, info in analysis.FEATURES.items()
    ]
    return DayDetail(
        date=day.date,
        label=analysis.label_day(day),
        score=analysis.score_day(day),
        survey=survey_of(day),
        features=features,
        deviations=analysis.day_deviations(days, day.date),
        summary=analysis.explain_day(days, day.date),
    )


def survey_of(day: Day) -> SurveyBase | None:
    if None in (day.mood, day.fatigue, day.sleep_quality, day.stress):
        return None
    return SurveyBase.model_validate(day, from_attributes=True)
