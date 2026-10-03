from fastapi.testclient import TestClient
from sqlmodel import Session


def test_calendar_range_and_headlines(client: TestClient, demo: Session) -> None:
    days = client.get("/api/users/p10/days?from=2019-11-16&to=2019-11-20").json()

    assert [d["date"] for d in days] == [f"2019-11-{n}" for n in range(16, 21)]
    by_date = {d["date"]: d for d in days}
    assert by_date["2019-11-20"]["label"] == "bad"
    assert by_date["2019-11-20"]["has_reason"] is True
    assert by_date["2019-11-20"]["headline"] == "Possible reason: awake 13.3% of night"
    assert all(len(d["top_deviations"]) <= 2 for d in days)


def test_day_detail_with_reason(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p10/days/2019-11-20").json()

    assert day["summary"] == "Possible reason: awake 13.3% of night"
    reason = day["reasons"][0]
    assert reason["feature"] == "wake_pct" and reason["display"] == "13.3%"
    assert reason["pattern_text"].startswith("Awake over 12% of night")
    assert day["survey"] == {"mood": 3, "fatigue": 2, "sleep_quality": 2, "stress": 1}
    sleep = next(f for f in day["features"] if f["feature"] == "sleep_h")
    assert sleep["display"] == "5h19" and sleep["when"] == "last_night"
    assert sleep["norm"]["average"] is not None and sleep["in_patterns"] is True
    assert all(d["text"].endswith("vs good days") for d in day["deviations"])


def test_bad_day_without_pattern(client: TestClient, demo: Session) -> None:
    bad = [d for d in client.get("/api/users/p06/days?to=2019-11-30").json() if d["label"] == "bad"]
    day = client.get(f"/api/users/p06/days/{bad[0]['date']}").json()

    assert day["reasons"] == []  # P06 has no significant bad-day pattern
    assert day["summary"] == "No clear reason"


def test_demo_data_ends_today_with_an_empty_check_in(client: TestClient, demo: Session) -> None:
    days = client.get("/api/users/p10/days").json()

    assert days[-1]["date"] == "2020-02-14" and days[-1]["label"] is None
    assert client.get("/api/users/p10/days/2020-02-15").status_code == 404


def test_day_not_found(client: TestClient, demo: Session) -> None:
    response = client.get("/api/users/p10/days/2030-01-01")

    assert response.status_code == 404
    assert response.json() == {"detail": "No data for 2030-01-01"}


def test_in_patterns_follows_group_e_choice(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p01/days/2019-11-20").json()
    flags = {f["feature"]: f["in_patterns"] for f in day["features"]}

    assert flags["z_cardio_peak"] is True and flags["mvpa"] is False  # p01 uses HR zones
    assert flags["sleep_eff"] is False  # view-only feature


def test_tile_headline_matches_day_summary(client: TestClient, demo: Session) -> None:
    tiles = client.get("/api/users/p06/days?to=2019-11-30").json()
    for tile in tiles:
        if tile["label"] in ("bad", "good"):
            detail = client.get(f"/api/users/p06/days/{tile['date']}").json()
            assert tile["headline"] == detail["summary"]


def test_timeline_highlights_where_the_reason_comes_from(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p01/days/2020-02-28").json()

    assert [p["offset"] for p in day["timeline"]] == [-3, -2, -1, 0]
    assert [p["date"] for p in day["timeline"]] == [
        "2020-02-25",
        "2020-02-26",
        "2020-02-27",
        "2020-02-28",
    ]
    highlighted = [
        (p["offset"], v["feature"], v["display"])
        for p in day["timeline"]
        for v in p["night"] + p["activity"]
        if v["highlight"]
    ]
    assert highlighted == [(-1, "z_cardio_peak", "68 min")]  # "the day before"
    night = {v["feature"] for v in day["timeline"][-1]["night"]}
    assert night == {"sleep_h", "bedtime_h", "wake_pct", "rem_pct", "hr_sleep_mean"}


def test_timeline_for_last_night_reason(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p10/days/2020-02-10").json()
    highlighted = {
        (p["offset"], v["feature"]) for p in day["timeline"] for v in p["night"] if v["highlight"]
    }

    assert highlighted == {(0, "wake_pct")}


def test_timeline_avg3_highlights_three_previous_days(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p16/days/2019-11-15").json()
    highlighted = {
        (p["offset"], v["feature"])
        for p in day["timeline"]
        for v in p["activity"]
        if v["highlight"]
    }

    assert highlighted == {(-3, "steps"), (-2, "steps"), (-1, "steps")}  # not today's steps
    steps = [
        v["value"] for p in day["timeline"][:3] for v in p["activity"] if v["feature"] == "steps"
    ]
    assert round(sum(steps) / 3, 3) == day["reasons"][0]["value"]


def test_timeline_hides_a_night_that_ended_after_the_check_in(
    client: TestClient, session: Session
) -> None:
    import datetime as dt

    from app.models import Day, Persona

    session.add(Persona(id="late", name="Late"))
    session.add(
        Day.model_validate(
            {
                "user_id": "late",
                "date": "2024-01-10",
                "sleep_minutes": 420,
                "sleep_start": dt.datetime(2024, 1, 9, 23, 0),
                "sleep_end": dt.datetime(2024, 1, 10, 9, 0),  # woke after the 06:00 check-in
                "mood": 3,
                "fatigue": 3,
                "sleep_quality": 3,
                "stress": 3,
                "survey_at": dt.datetime(2024, 1, 10, 5, 0, tzinfo=dt.UTC),  # 06:00 Oslo
            }
        )
    )
    session.commit()

    day = client.get("/api/users/late/days/2024-01-10").json()

    assert next(f for f in day["features"] if f["feature"] == "sleep_h")["value"] is None
    assert day["timeline"][-1]["night"] == []


def test_new_user_day_view(client: TestClient, demo: Session) -> None:
    user = client.post("/api/users", json={"name": "Maja"}).json()
    answers = {"mood": 3, "fatigue": 3, "sleep_quality": 3, "stress": 3}
    client.put(f"/api/users/{user['id']}/surveys/{user['today']}", json=answers)

    day = client.get(f"/api/users/{user['id']}/days/{user['today']}").json()

    assert [p["label"] for p in day["timeline"]] == [None, None, None, "neutral"]
    assert all(p["night"] == [] and p["activity"] == [] for p in day["timeline"])


def test_leans_follows_the_users_own_good_and_bad_days(client: TestClient, demo: Session) -> None:
    stats = {f["feature"]: f for f in client.get("/api/users/p10/stats").json()["features"]}
    day = client.get("/api/users/p10/days/2020-02-14").json()

    # Sam's bad days have less sleep than good days; 4 h 53 min is below the good-day average
    assert stats["sleep_h"]["difference"] < 0
    sleep = next(d for d in day["deviations"] if d["feature"] == "sleep_h")
    assert (sleep["direction"], sleep["leans"]) == ("lower", "bad")
    features = {f["feature"]: f for f in day["features"]}
    assert features["sleep_h"]["leans"] == "bad"
    # bedtime is about the same on good and bad days: no lean either way
    assert features["bedtime_h"]["leans"] is None


def test_no_leans_with_few_good_days(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p01/days/2020-03-06").json()  # Robin: 3 good days

    assert all(f["leans"] is None for f in day["features"])
    assert all(d["leans"] is None for d in day["deviations"])
