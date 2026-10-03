import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_list_demo_personas(client: TestClient, demo: Session) -> None:
    users = client.get("/api/users").json()

    assert [u["id"] for u in users] == ["p06", "p01", "p10", "p16"]  # switcher order
    assert [u["name"] for u in users] == ["Alex", "Robin", "Sam", "Kim"]
    assert all(u["insights_status"] == "ok" and u["is_demo"] for u in users)
    p06 = users[0]
    assert p06["today"] == "2020-03-08"
    assert p06["demo_answers"] == {"mood": 4, "fatigue": 3, "sleep_quality": 3, "stress": 4}
    assert p06["days_with_data"] == 122 and p06["days_needed"] == 60
    assert p06["first_date"] == "2019-11-01"


def test_unknown_persona(client: TestClient, demo: Session) -> None:
    response = client.get("/api/users/p99")

    assert response.status_code == 404
    assert response.json() == {"detail": "Persona p99 not found"}


def test_persona_without_days_does_not_break_the_list(client: TestClient, demo: Session) -> None:
    from app.models import Persona

    demo.add(Persona(id="empty", name="Empty"))
    demo.commit()

    users = {u["id"]: u for u in client.get("/api/users").json()}

    assert users["empty"]["insights_status"] == "insufficient_days"
    assert users["empty"]["days_with_data"] == 0
    assert client.get("/api/users/empty/days").json() == []
    assert client.get("/api/users/empty/patterns").json()["status"] == "insufficient_days"


def test_label_mode_and_norm_reference(client: TestClient, demo: Session) -> None:
    users = {u["id"]: u for u in client.get("/api/users").json()}

    assert users["p06"]["label_mode"] == "personal"
    assert users["p06"]["norm_reference"] == "good_days"
    assert users["p01"]["norm_reference"] == "all_days"  # only 3 good days


def test_malformed_demo_answers_are_ignored(client: TestClient, demo: Session) -> None:
    import pytest
    from pydantic import ValidationError

    from app.models import Persona

    with pytest.raises(ValidationError):
        Persona.model_validate({"id": "x", "name": "X", "demo_answers": "3.0,3,3,3"})
    persona = demo.get(Persona, "p10")
    persona.demo_answers = "3,3"  # bypasses validation, like a hand-edited row
    demo.add(persona)
    demo.commit()

    users = {u["id"]: u for u in client.get("/api/users").json()}

    assert users["p10"]["demo_answers"] is None


def test_onboarding_creates_a_real_user(client: TestClient, demo: Session) -> None:
    response = client.post("/api/users", json={"name": "Maja"})

    assert response.status_code == 201
    user = response.json()
    assert user["id"].startswith("u") and user["name"] == "Maja"
    assert user["is_demo"] is False and user["days_count"] == 0
    assert user["insights_status"] == "insufficient_days"
    assert (user["days_with_data"], user["days_needed"]) == (0, 60)
    assert [u["id"] for u in client.get("/api/users").json()][-1] == user["id"]

    check_in = {"mood": 4, "fatigue": 4, "sleep_quality": 4, "stress": 4}
    saved = client.put(f"/api/users/{user['id']}/surveys/{user['today']}", json=check_in)
    assert saved.status_code == 200 and saved.json()["label"] == "good"


def test_onboarding_validation(client: TestClient) -> None:
    assert client.post("/api/users", json={"name": ""}).status_code == 422
    assert client.post("/api/users", json={}).status_code == 422


def test_onboarding_rejects_blank_name_and_deletes_users(client: TestClient, demo: Session) -> None:
    assert client.post("/api/users", json={"name": "   "}).status_code == 422
    user = client.post("/api/users", json={"name": "  Maja "}).json()
    assert user["name"] == "Maja" and len(user["id"]) == 13

    assert client.delete(f"/api/users/{user['id']}").status_code == 204
    assert client.get(f"/api/users/{user['id']}").status_code == 404
    assert client.delete("/api/users/p10").status_code == 403  # demo persona


def test_demo_reset_keeps_onboarded_users(
    client: TestClient, demo: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "demo_reset", True)
    user = client.post("/api/users", json={"name": "Maja"}).json()

    client.post("/api/demo/reset")

    ids = [u["id"] for u in client.get("/api/users").json()]
    assert ids == ["p06", "p01", "p10", "p16", user["id"]]
