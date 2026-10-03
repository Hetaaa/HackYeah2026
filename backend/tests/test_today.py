import datetime as dt

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Persona


def test_heads_up_before_check_in(client: TestClient, demo: Session) -> None:
    today = client.get("/api/users/p10/today").json()

    assert today["date"] == "2020-02-14" and today["survey"] is None
    assert today["outlook"] == "tough"
    assert today["summary"] == "Today may be tougher than usual. Check in to see how you feel."
    signal = today["heads_up"][0]
    assert signal["feature"] == "wake_pct" and signal["when"] == "last_night"
    assert signal["text"] == "Heads-up: you were awake 12.5% of last night."
    assert signal["pattern_text"].startswith("When you are awake over 12% of the night")
    assert today["has_watch_data"] and today["features"]


def test_live_check_in_explains_the_day(client: TestClient, demo: Session) -> None:
    persona = client.get("/api/users/p10").json()

    saved = client.put(f"/api/users/p10/surveys/{persona['today']}", json=persona["demo_answers"])
    today = client.get("/api/users/p10/today").json()

    assert saved.json()["label"] == "bad"
    assert today["survey"]["label"] == "bad"
    assert today["summary"] == "Possible reason: you were awake 12.5% of last night."
    assert client.get("/api/users/p10/patterns").json()["status"] == "ok"  # pattern survives


def test_good_sign(client: TestClient, demo: Session) -> None:
    today = client.get("/api/users/p06/today").json()

    assert today["outlook"] == "promising" and today["heads_up"] == []
    assert today["good_signs"][0]["text"] == "Good sign: you slept 7 h 23 min last night."


def test_check_in_after_demo_today_is_rejected(client: TestClient, demo: Session) -> None:
    answers = {"mood": 3, "fatigue": 3, "sleep_quality": 3, "stress": 3}

    assert client.put("/api/users/p10/surveys/2020-02-15", json=answers).status_code == 422


def test_real_user_today_without_watch_data(client: TestClient, session: Session) -> None:
    session.add(Persona(id="new", name="New"))
    session.commit()

    user = client.get("/api/users/new").json()
    today = client.get("/api/users/new/today").json()

    assert user["is_demo"] is False and user["demo_answers"] is None
    assert user["today"] == dt.datetime.now(dt.UTC).date().isoformat()
    assert today["outlook"] == "unknown" and today["summary"] == "No watch data for today yet."


def test_demo_reset_undoes_check_ins(client: TestClient, demo: Session) -> None:
    answers = client.get("/api/users/p10").json()["demo_answers"]
    client.put("/api/users/p10/surveys/2020-02-14", json=answers)

    response = client.post("/api/demo/reset")

    assert response.status_code == 200 and response.json() == {"personas": 4, "days": 477}
    assert client.get("/api/users/p10/today").json()["survey"] is None
