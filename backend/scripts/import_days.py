"""Import personas and days from CSV.

days.csv: one row = one day of one user. Columns: user_id, date + any field of app.models.Day
(watch data, survey answers, survey_at). Empty cells are allowed. Existing days of the
same user and date are overwritten.
personas.csv (optional): id, name, description, analysis_window_end.

Run with: uv run python -m scripts.import_days data/demo/days.csv [data/demo/personas.csv]
"""

import csv
import sys
from pathlib import Path

from sqlmodel import Session, select

from app.models import Day, Persona

TEXT_COLUMNS = {"user_id", "date", "sleep_type", "sleep_start", "sleep_end", "survey_at"}
DAY_COLUMNS = set(Day.model_fields) - {"id"}


def parse_row(row: dict[str, str]) -> dict[str, object]:
    data: dict[str, object] = {}
    for column, raw in row.items():
        if column not in DAY_COLUMNS:
            continue
        value = (raw or "").strip()
        if not value:
            data[column] = None
        elif column in TEXT_COLUMNS:
            data[column] = value
        else:
            data[column] = float(value)
    return data


def import_personas(session: Session, path: Path, commit: bool = True) -> int:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        data = {k: (v or None) for k, v in row.items()}
        persona = session.get(Persona, data["id"])
        if persona is None:
            session.add(Persona.model_validate(data))
        else:
            persona.sqlmodel_update(Persona.model_validate(data).model_dump())
            session.add(persona)
    session.flush()
    if commit:
        session.commit()
    return len(rows)


def import_days(session: Session, path: Path, commit: bool = True) -> int:
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
    if commit:
        session.commit()
    return len(rows)


if __name__ == "__main__":
    from app.db import engine, init_db

    init_db(engine)
    with Session(engine) as session:
        if len(sys.argv) > 2:
            print(f"Imported {import_personas(session, Path(sys.argv[2]))} personas")
        count = import_days(session, Path(sys.argv[1]))
    print(f"Imported {count} days into {engine.url}")
