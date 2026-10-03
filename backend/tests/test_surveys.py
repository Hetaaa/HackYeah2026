from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Persona

ANSWERS = {"mood": 1, "fatigue": 1, "sleep_quality": 2, "stress": 1}


def test_save_survey_returns_personal_label(client: TestClient, demo: Session) -> None:
    assert client.get("/api/users/p10/surveys/2020-03-05").status_code == 404

    response = client.put("/api/users/p10/surveys/2020-03-05", json=ANSWERS)

    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "bad" and body["score"] < -0.5
    assert client.get("/api/users/p10/surveys/2020-03-05").json() == body
    assert client.get("/api/users/p10/days/2020-03-05").json()["label"] == "bad"


def test_first_survey_of_new_user_uses_absolute_label(client: TestClient, session: Session) -> None:
    session.add(Persona(id="new", name="New"))
    session.commit()

    body = client.put(
        "/api/users/new/surveys/2024-01-01",
        json={"mood": 4, "fatigue": 4, "sleep_quality": 4, "stress": 4},
    ).json()

    assert body["label"] == "good" and body["score"] == 1


def test_survey_validation(client: TestClient, demo: Session) -> None:
    response = client.put("/api/users/p10/surveys/2020-03-05", json=ANSWERS | {"mood": 6})

    assert response.status_code == 422
