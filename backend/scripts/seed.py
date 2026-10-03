"""Demo data. Run: uv run python -m scripts.seed

Real PMData personas from data/demo/*.csv (made by scripts/import_pmdata.py) when present,
otherwise generated personas with a planted bad-day pattern each.
"""

import datetime as dt
import random
from pathlib import Path

from sqlmodel import Session, func, select

from app.models import Day, Persona
from scripts.import_days import import_days, import_personas

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"

START_DATE = dt.date(2019, 11, 1)
DAYS_COUNT = 150

PERSONAS: list[dict[str, str]] = [
    {"id": "p01", "name": "Alex", "description": "Bad days tend to follow short nights."},
    {"id": "p02", "name": "Sam", "description": "Bad days tend to follow low-activity days."},
    {
        "id": "p03",
        "name": "Jordan",
        "description": "Bad days come with a raised heart rate during sleep.",
    },
]


def generate_days(user_id: str, rng: random.Random) -> list[Day]:
    """Days with a planted cause of bad days, aligned like real data: last night's sleep or
    sleep heart rate (p01, p03) and the previous day's activity (p02) shape the morning check-in.
    Uses normalvariate: gauss caches Box-Muller pairs, which couples unrelated draws."""
    normal = rng.normalvariate
    triggered, state = [], False
    for _ in range(DAYS_COUNT + 1):
        state = rng.random() < (0.45 if state else 0.2)
        triggered.append(state)
    days: list[Day] = []
    for offset in range(DAYS_COUNT):
        bad = triggered[offset]
        sleep = normal(450, 30)
        resting_hr = normal(58, 1.5)
        sleep_hr = resting_hr + normal(4, 1)
        steps = normal(9000, 1800)
        active = normal(50, 12)
        if bad and user_id == "p01":
            sleep -= normal(110, 20)
        if triggered[offset + 1] and user_id == "p02":  # low activity the day before a bad day
            steps, active = normal(3000, 700), normal(10, 4)
        if bad and user_id == "p03":
            resting_hr += normal(7, 1.5)
            sleep_hr += normal(7, 1.5)
        wellness = normal(3.9, 0.35) - (1.7 if bad else 0)
        survey = {
            name: min(5, max(1, round(normal(wellness, 0.5))))
            for name in ("mood", "fatigue", "sleep_quality", "stress")
        }
        has_survey = offset < DAYS_COUNT - 1 and rng.random() > 0.05
        days.append(
            Day.model_validate(
                {
                    "user_id": user_id,
                    "date": START_DATE + dt.timedelta(days=offset),
                    "sleep_minutes": round(sleep),
                    "resting_hr": round(resting_hr),
                    "sleep_hr_mean": round(sleep_hr, 1),
                    "steps": round(max(steps, 300)),
                    "active_minutes": round(max(active, 0)),
                    "calories": round(1900 + 0.045 * steps + 4 * active),
                    **(survey if has_survey else {}),
                }
            )
        )
    return days


def seed(session: Session) -> None:
    if (DEMO_DIR / "days.csv").exists():
        import_personas(session, DEMO_DIR / "personas.csv")
        import_days(session, DEMO_DIR / "days.csv")
        return
    seed_generated(session)


def seed_generated(session: Session) -> None:
    for index, data in enumerate(PERSONAS):
        session.add(Persona.model_validate(data))
        session.add_all(generate_days(data["id"], random.Random(index)))
    session.commit()


def seed_if_empty(session: Session) -> bool:
    count = session.exec(select(func.count()).select_from(Persona)).one()
    if count:
        return False
    seed(session)
    return True


if __name__ == "__main__":
    from app.db import engine, init_db

    init_db(engine)
    with Session(engine) as session:
        inserted = seed_if_empty(session)
    print("Seeded demo personas." if inserted else "Persona table not empty, skipping seed.")
