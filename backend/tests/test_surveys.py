from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Persona

ANSWERS = {"mood": 1, "fatigue": 1, "sleep_quality": 2, "stress": 1}


def test_save_survey_returns_personal_label(client: TestClient, demo: Session) -> None:
    assert client.get("/api/users/p10/surveys/2020-02-14").status_code == 404

    response = client.put("/api/users/p10/surveys/2020-02-14", json=ANSWERS)

    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "bad" and body["score"] < -0.5
    assert client.get("/api/users/p10/surveys/2020-02-14").json() == body
    assert client.get("/api/users/p10/days/2020-02-14").json()["label"] == "bad"


def test_first_survey_of_new_user_uses_absolute_label(client: TestClient, session: Session) -> None:
    session.add(Persona(id="new", name="New"))
    session.commit()

    body = client.put(
        "/api/users/new/surveys/2024-01-01",
        json={"mood": 4, "fatigue": 4, "sleep_quality": 4, "stress": 4},
    ).json()

    assert body["label"] == "good" and body["score"] == 1


def test_survey_validation(client: TestClient, demo: Session) -> None:
    response = client.put("/api/users/p10/surveys/2020-02-14", json=ANSWERS | {"mood": 6})

    assert response.status_code == 422


def test_survey_date_out_of_range(client: TestClient, demo: Session) -> None:
    for date in ("1677-01-01", "1999-12-31", "2300-01-01"):
        response = client.put(f"/api/users/p10/surveys/{date}", json=ANSWERS)
        assert response.status_code == 422, date
    assert client.get("/api/users").status_code == 200


def test_editing_a_survey_keeps_its_time(client: TestClient, demo: Session) -> None:
    from sqlmodel import select

    from app.models import Day

    client.put("/api/users/p10/surveys/2020-02-14", json=ANSWERS)
    first = demo.exec(select(Day).where(Day.user_id == "p10", Day.date == "2020-02-14")).one()
    first_at = first.survey_at

    client.put("/api/users/p10/surveys/2020-02-14", json=ANSWERS | {"mood": 2})
    demo.refresh(first)

    assert first.mood == 2 and first.survey_at == first_at


def test_new_survey_refits_other_days(client: TestClient, demo: Session) -> None:
    before = client.get("/api/users/p10/days/2019-11-20").json()["score"]

    client.put("/api/users/p10/surveys/2020-02-14", json=ANSWERS)

    after = client.get("/api/users/p10/days/2019-11-20").json()["score"]
    assert after != before  # labels are relative to the whole personal history


def test_identical_answers_keep_labels(client: TestClient, session: Session) -> None:
    session.add(Persona(id="flat", name="Flat"))
    session.commit()
    same = {"mood": 3, "fatigue": 3, "sleep_quality": 3, "stress": 3}
    for day in range(1, 17):  # crosses the 14 check-in boundary
        body = client.put(f"/api/users/flat/surveys/2024-01-{day:02d}", json=same).json()
        assert body["label"] == "neutral", day

    assert client.get("/api/users/flat").json()["label_mode"] == "absolute"


def test_delete_survey(client: TestClient, demo: Session) -> None:
    client.put("/api/users/p10/surveys/2020-02-14", json=ANSWERS)

    assert client.delete("/api/users/p10/surveys/2020-02-14").status_code == 204

    assert client.get("/api/users/p10/surveys/2020-02-14").status_code == 404
    day = client.get("/api/users/p10/days/2020-02-14").json()
    assert day["survey"] is None and day["label"] is None
    assert client.delete("/api/users/p10/surveys/2020-02-14").status_code == 404
