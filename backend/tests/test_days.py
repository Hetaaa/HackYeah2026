from fastapi.testclient import TestClient
from sqlmodel import Session


def test_calendar_range_and_headlines(client: TestClient, demo: Session) -> None:
    days = client.get("/api/users/p10/days?from=2019-11-16&to=2019-11-20").json()

    assert [d["date"] for d in days] == [f"2019-11-{n}" for n in range(16, 21)]
    by_date = {d["date"]: d for d in days}
    assert by_date["2019-11-20"]["label"] == "bad"
    assert by_date["2019-11-20"]["has_reason"] is True
    assert (
        by_date["2019-11-20"]["headline"] == "Possible reason: you were awake 13.3% of last night."
    )
    assert all(len(d["top_deviations"]) <= 2 for d in days)


def test_day_detail_with_reason(client: TestClient, demo: Session) -> None:
    day = client.get("/api/users/p10/days/2019-11-20").json()

    assert day["summary"] == "Possible reason: you were awake 13.3% of last night."
    reason = day["reasons"][0]
    assert reason["feature"] == "wake_pct" and reason["display"] == "13.3%"
    assert reason["pattern_text"].startswith("When you are awake over 12% of the night")
    assert day["survey"] == {"mood": 3, "fatigue": 2, "sleep_quality": 2, "stress": 1}
    sleep = next(f for f in day["features"] if f["feature"] == "sleep_h")
    assert sleep["display"] == "5 h 19 min" and sleep["when"] == "last_night"
    assert sleep["norm"]["average"] is not None and sleep["in_patterns"] is True
    assert all(d["text"].endswith("than on your average good day.") for d in day["deviations"])


def test_bad_day_without_pattern(client: TestClient, demo: Session) -> None:
    bad = [d for d in client.get("/api/users/p06/days?to=2019-11-30").json() if d["label"] == "bad"]
    day = client.get(f"/api/users/p06/days/{bad[0]['date']}").json()

    assert day["reasons"] == []  # P06 has no significant bad-day pattern
    assert day["summary"] == "No clear pattern explains this day."


def test_day_after_window_is_flagged(client: TestClient, demo: Session) -> None:
    assert client.get("/api/users/p06/days/2020-03-20").json()["outside_window"] is True


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
