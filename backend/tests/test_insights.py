import datetime as dt

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Day, Persona


def test_bad_day_patterns(client: TestClient, demo: Session) -> None:
    report = client.get("/api/users/p10/patterns").json()

    assert report["status"] == "ok"
    assert report["summary"] == "We found 1 possible reason behind your bad days."
    pattern = report["patterns"][0]
    assert pattern["feature"] == "wake_pct" and pattern["condition"] == "over 12%"
    assert pattern["level"] == "significant" and pattern["p_value"] <= 0.05
    assert (pattern["days_in_condition"], pattern["target_days_in_condition"]) == (30, 16)
    assert pattern["bad_share"] > pattern["good_share"]
    assert len(pattern["example_dates"]) == 3


def test_recipe(client: TestClient, demo: Session) -> None:
    recipe = client.get("/api/users/p16/recipe").json()

    assert recipe["status"] == "ok"
    assert recipe["ingredients"][0]["condition"] == "more than 3,000 steps"
    assert recipe["ingredients"][0]["when"] == "previous_3_days"


def test_recipe_needs_good_days(client: TestClient, demo: Session) -> None:
    recipe = client.get("/api/users/p01/recipe").json()

    assert recipe["status"] == "insufficient_good_days"
    assert recipe["ingredients"] == []
    assert recipe["summary"] == "Not enough good days yet to write your recipe."


def test_new_user_is_collecting_data(client: TestClient, session: Session) -> None:
    session.add(Persona(id="new", name="New"))
    for offset in range(10):
        session.add(
            Day.model_validate(
                {
                    "user_id": "new",
                    "date": dt.date(2024, 1, 1) + dt.timedelta(days=offset),
                    "sleep_minutes": 420,
                    "steps": 8000,
                    "mood": 3,
                    "fatigue": 3,
                    "sleep_quality": 3,
                    "stress": 3,
                }
            )
        )
    session.commit()

    report = client.get("/api/users/new/patterns").json()

    assert report["status"] == "insufficient_days"
    assert report["summary"].startswith("Keep checking in: insights appear after 60 days")
    assert client.get("/api/users/new").json()["insights_status"] == "insufficient_days"
