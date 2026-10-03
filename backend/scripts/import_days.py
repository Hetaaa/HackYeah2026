"""Import days from a CSV (one row = one day of one user).

Columns: user_id, date, sleep_minutes, resting_hr, steps, active_minutes, calories,
mood, fatigue, sleep_quality, stress. Empty cells are allowed. Existing days are overwritten.

Run with: uv run python -m scripts.import_days data/days.csv
"""

import csv
import sys
from pathlib import Path

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Day, Persona

NUMERIC_COLUMNS = (
    "sleep_minutes",
    "resting_hr",
    "steps",
    "active_minutes",
    "calories",
    "mood",
    "fatigue",
    "sleep_quality",
    "stress",
)


def parse_row(row: dict[str, str]) -> dict[str, object]:
    data: dict[str, object] = {"user_id": row["user_id"], "date": row["date"]}
    for column in NUMERIC_COLUMNS:
        value = (row.get(column) or "").strip()
        data[column] = float(value) if value else None
    return data


def import_days(session: Session, path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as file:
        rows = [parse_row(row) for row in csv.DictReader(file)]
    for data in rows:
        user_id = str(data["user_id"])
        if session.get(Persona, user_id) is None:
            session.add(Persona(id=user_id, name=user_id))
        new_day = Day.model_validate(data)
        day = session.exec(
            select(Day).where(Day.user_id == new_day.user_id, Day.date == new_day.date)
        ).first()
        if day is None:
            session.add(new_day)
        else:
            day.sqlmodel_update(new_day.model_dump(exclude={"id"}))
            session.add(day)
        session.flush()
    session.commit()
    return len(rows)


if __name__ == "__main__":
    init_db(engine)
    with Session(engine) as session:
        count = import_days(session, Path(sys.argv[1]))
    print(f"Imported {count} days into {engine.url}")
