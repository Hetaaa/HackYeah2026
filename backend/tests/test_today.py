import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.models import Persona


def test_heads_up_before_check_in(client: TestClient, demo: Session) -> None:
    today = client.get("/api/users/p10/today").json()

    assert today["date"] == "2020-02-14" and today["survey"] is None
    assert today["outlook"] == "tough"
    assert today["summary"] == "Tougher day possible"
    signal = today["heads_up"][0]
    assert signal["feature"] == "wake_pct" and signal["when"] == "last_night"
    assert signal["text"] == "Heads-up: awake 12.5% of night"
    assert signal["pattern_text"].startswith("Awake over 12% of night")
    assert today["has_watch_data"] and today["features"]


def test_live_check_in_explains_the_day(client: TestClient, demo: Session) -> None:
    persona = client.get("/api/users/p10").json()

    saved = client.put(f"/api/users/p10/surveys/{persona['today']}", json=persona["demo_answers"])
    today = client.get("/api/users/p10/today").json()

    assert saved.json()["label"] == "bad"
    assert today["survey"]["label"] == "bad"
    assert today["summary"] == "Possible reason: awake 12.5% of night"
    assert client.get("/api/users/p10/patterns").json()["status"] == "ok"  # pattern survives


def test_good_sign(client: TestClient, demo: Session) -> None:
    today = client.get("/api/users/p06/today").json()

    assert today["outlook"] == "promising" and today["heads_up"] == []
    assert today["good_signs"][0]["text"] == "Good sign: 7h23 sleep"


def test_check_in_after_demo_today_is_rejected(client: TestClient, demo: Session) -> None:
    answers = {"mood": 3, "fatigue": 3, "sleep_quality": 3, "stress": 3}

    assert client.put("/api/users/p10/surveys/2020-02-15", json=answers).status_code == 422


def test_real_user_today_without_watch_data(client: TestClient, session: Session) -> None:
    session.add(Persona(id="new", name="New"))
    session.commit()

    user = client.get("/api/users/new").json()
    today = client.get("/api/users/new/today").json()

    assert user["is_demo"] is False and user["demo_answers"] is None
    assert user["today"] == dt.datetime.now(ZoneInfo("Europe/Oslo")).date().isoformat()
    assert today["outlook"] == "unknown" and today["summary"] == "No watch data yet"


def test_heads_up_stays_after_check_in(client: TestClient, demo: Session) -> None:
    before = client.get("/api/users/p10/today").json()["heads_up"]

    client.put(
        "/api/users/p10/surveys/2020-02-14",
        json={"mood": 5, "fatigue": 5, "sleep_quality": 5, "stress": 5},
    )
    after = client.get("/api/users/p10/today").json()

    assert after["heads_up"] == before  # morning signals ignore today's answers
    assert after["survey"]["label"] == "good"


def test_every_persona_has_a_story_today(client: TestClient, demo: Session) -> None:
    for user in client.get("/api/users").json():
        today = client.get(f"/api/users/{user['id']}/today").json()
        expected = "promising" if user["id"] == "p06" else "tough"
        assert today["outlook"] == expected, user["id"]

        saved = client.put(
            f"/api/users/{user['id']}/surveys/{user['today']}", json=user["demo_answers"]
        ).json()
        reasons = client.get(f"/api/users/{user['id']}/days/{user['today']}").json()["reasons"]
        assert saved["label"] == ("good" if user["id"] == "p06" else "bad"), user["id"]
        signals = today["heads_up"] + today["good_signs"]
        assert reasons[0]["feature"] == signals[0]["feature"], user["id"]


def test_demo_reset_is_opt_in(client: TestClient, demo: Session) -> None:
    response = client.post("/api/demo/reset")

    assert response.status_code == 403
    assert response.json() == {"detail": "Demo reset is disabled"}


def test_demo_reset_undoes_check_ins_and_keeps_other_users(
    client: TestClient, demo: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "demo_reset", True)
    demo.add(Persona(id="real", name="Real user"))
    demo.commit()
    answers = client.get("/api/users/p10").json()["demo_answers"]
    client.put("/api/users/p10/surveys/2020-02-14", json=answers)

    response = client.post("/api/demo/reset")

    assert response.status_code == 200 and response.json() == {"personas": 4, "days": 477}
    assert client.get("/api/users/p10/today").json()["survey"] is None
    assert client.get("/api/users/real").status_code == 200
