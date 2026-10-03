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
