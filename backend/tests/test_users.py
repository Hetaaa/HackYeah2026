from fastapi.testclient import TestClient
from sqlmodel import Session


def test_list_demo_personas(client: TestClient, demo: Session) -> None:
    users = client.get("/api/users").json()

    assert [u["id"] for u in users] == ["p01", "p06", "p10", "p16"]
    assert [u["name"] for u in users] == ["Robin", "Alex", "Sam", "Kim"]
    assert all(u["insights_status"] == "ok" for u in users)
    p06 = users[1]
    assert p06["days_with_data"] == 144 and p06["days_needed"] == 60
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
