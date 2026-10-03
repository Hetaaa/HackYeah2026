import datetime as dt

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Day, Persona


def test_bad_day_patterns(client: TestClient, demo: Session) -> None:
    report = client.get("/api/users/p10/patterns").json()

    assert report["status"] == "ok"
    assert report["summary"] == "1 possible reason for bad days"
    pattern = report["patterns"][0]
    assert pattern["feature"] == "wake_pct" and pattern["condition"] == "Awake over 12% of night"
    assert pattern["level"] == "significant" and pattern["p_value"] <= 0.05
    assert (pattern["days_in_condition"], pattern["target_days_in_condition"]) == (27, 15)
    assert pattern["bad_share"] > pattern["good_share"]
    assert len(pattern["example_dates"]) == 3


def test_recipe(client: TestClient, demo: Session) -> None:
    recipe = client.get("/api/users/p16/recipe").json()

    assert recipe["status"] == "ok"
    assert recipe["ingredients"][0]["condition"] == "Over 3k steps (3-day avg)"
    assert recipe["ingredients"][0]["when"] == "previous_3_days"


def test_recipe_needs_good_days(client: TestClient, demo: Session) -> None:
    recipe = client.get("/api/users/p01/recipe").json()

    assert recipe["status"] == "insufficient_good_days"
    assert recipe["ingredients"] == []
    assert recipe["summary"] == "Not enough good days yet"


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
    assert report["summary"].endswith("/60 days")
    assert client.get("/api/users/new").json()["insights_status"] == "insufficient_days"


def test_pattern_chart(client: TestClient, demo: Session) -> None:
    chart = client.get("/api/users/p10/patterns/wake_pct").json()
    pattern = client.get("/api/users/p10/patterns").json()["patterns"][0]

    assert chart["condition"] == "Awake over 12% of night" and chart["display_threshold"] == "12%"
    inside = [p for p in chart["points"] if p["in_condition"]]
    assert len(inside) == pattern["days_in_condition"] == chart["days_in_condition"]
    assert sum(p["label"] == "bad" for p in inside) == pattern["target_days_in_condition"]
    assert all((p["value"] > 12) == p["in_condition"] for p in chart["points"])
    dates = [p["date"] for p in chart["points"]]
    assert dates == sorted(dates)


def test_recipe_chart_and_missing_pattern(client: TestClient, demo: Session) -> None:
    recipe = client.get("/api/users/p10/patterns/lightly?kind=good").json()

    assert recipe["kind"] == "good"
    assert recipe["condition"] == "Over 5h20 light activity (day before)"
    assert client.get("/api/users/p10/patterns/steps").status_code == 404
    assert client.get("/api/users/p10/patterns/lightly?kind=meh").status_code == 422


def test_chart_shape_and_preliminary_pattern(client: TestClient, demo: Session) -> None:
    chart = client.get("/api/users/p06/patterns/sleep_h").json()

    assert chart["level"] == "preliminary" and chart["op"] == "below" and chart["variant"] == "lag1"
    assert sum(p["in_condition"] for p in chart["points"]) == chart["days_in_condition"]


def test_chart_for_the_unused_exercise_feature_is_404(client: TestClient, demo: Session) -> None:
    assert "mvpa" not in client.get("/api/users/p01").json()["pattern_features"]
    assert client.get("/api/users/p01/patterns/mvpa").status_code == 404


def test_stats_compare_good_and_bad_days(client: TestClient, demo: Session) -> None:
    report = client.get("/api/users/p10/stats").json()

    assert report["analysed_days"] == 66
    assert (report["good_days_count"], report["bad_days_count"]) == (32, 20)
    assert (report["date_from"], report["date_to"]) == ("2019-11-16", "2020-02-13")
    stats = {f["feature"]: f for f in report["features"]}
    wake = stats["wake_pct"]
    assert wake["in_patterns"] and wake["when"] == "last_night"
    assert (wake["good"]["display"], wake["bad"]["display"]) == ("11.0%", "13.4%")
    assert wake["good"]["days"] == 32
    assert wake["difference"] == round(wake["bad"]["average"] - wake["good"]["average"], 3)
    assert stats["bedtime_h"]["good"]["display"] == "00:20"
    assert not stats["mvpa"]["in_patterns"]  # p10 uses z_cardio_peak for exercise


def test_stats_without_check_ins(client: TestClient, session: Session) -> None:
    session.add(Persona(id="new", name="New"))
    session.commit()

    report = client.get("/api/users/new/stats").json()

    assert report["analysed_days"] == 0 and report["date_from"] is None
    sleep = next(f for f in report["features"] if f["feature"] == "sleep_h")
    assert sleep["good"] == {"average": None, "display": None, "days": 0}
    assert sleep["difference"] is None
