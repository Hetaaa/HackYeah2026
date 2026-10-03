from pathlib import Path

import pytest
from sqlmodel import Session, func, select

from app.models import Day, Persona
from scripts import seed as seed_module
from scripts.import_days import parse_row


def test_parse_row_types() -> None:
    row = parse_row(
        {
            "user_id": "p01",
            "date": "2019-11-02",
            "steps": "17873",
            "sleep_type": "stages",
            "sleep_start": "2019-11-01T23:10:00",
            "mood": "",
            "unknown": "x",
        }
    )

    assert row == {
        "user_id": "p01",
        "date": "2019-11-02",
        "steps": 17873.0,
        "sleep_type": "stages",
        "sleep_start": "2019-11-01T23:10:00",
        "mood": None,
    }


def test_seed_loads_demo_csv(session: Session) -> None:
    seed_module.seed(session)

    assert session.exec(select(func.count()).select_from(Persona)).one() == 4
    day = session.exec(select(Day).where(Day.user_id == "p06", Day.date == "2019-11-02")).one()
    assert day.sleep_type == "stages" and day.survey_at is not None


def test_seed_falls_back_to_generated(
    session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(seed_module, "DEMO_DIR", tmp_path)

    seed_module.seed(session)

    assert [p.id for p in session.exec(select(Persona).order_by(Persona.id))] == [
        "p01",
        "p02",
        "p03",
    ]
