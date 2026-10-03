"""Generated demo data until the PMData import is ready. Run: uv run python -m scripts.seed"""

import datetime as dt
import random

from sqlmodel import Session, func, select

from app.models import Day, Persona

START_DATE = dt.date(2019, 11, 1)
DAYS_COUNT = 150

PERSONAS: list[dict[str, str]] = [
    {"id": "p01", "name": "Alex", "description": "Bad days tend to follow short nights."},
    {"id": "p02", "name": "Sam", "description": "Bad days tend to follow low-activity days."},
    {
        "id": "p03",
        "name": "Jordan",
        "description": "Bad days come with a raised resting HR.",
    },
]


def generate_days(user_id: str, rng: random.Random) -> list[Day]:
    days: list[Day] = []
    triggered = False
    for offset in range(DAYS_COUNT):
        triggered = rng.random() < (0.45 if triggered else 0.2)
        sleep = rng.gauss(450, 30)
        resting_hr = rng.gauss(58, 1.5)
        steps = rng.gauss(9000, 1800)
        active = rng.gauss(50, 12)
        if triggered and user_id == "p01":
            sleep -= rng.gauss(110, 20)
        if triggered and user_id == "p02":
            steps, active = rng.gauss(3000, 700), rng.gauss(10, 4)
        if triggered and user_id == "p03":
            resting_hr += rng.gauss(7, 1.5)
        wellness = rng.gauss(3.9, 0.35) - (1.7 if triggered else 0)
        survey = {
            name: min(5, max(1, round(rng.gauss(wellness, 0.5))))
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
                    "steps": round(max(steps, 300)),
                    "active_minutes": round(max(active, 0)),
                    "calories": round(1900 + 0.045 * steps + 4 * active),
                    **(survey if has_survey else {}),
                }
            )
        )
    return days


def seed(session: Session) -> None:
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
