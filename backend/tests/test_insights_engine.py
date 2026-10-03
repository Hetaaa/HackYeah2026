"""Algorithm tests on synthetic watch data (no PMData needed)."""

import numpy as np
import pandas as pd
import pytest

from app.insights import cleaning, engine, fitbit
from app.insights import config as C
from app.insights.analyze import analyze_user
from app.insights.user import UserData


def synthetic_user(n_days: int = 120, effect: bool = True, seed: int = 0) -> UserData:
    """Fully worn watch, one main sleep per night, morning check-ins.

    effect=True: nights under 6 h make a bad day likely (70 %), otherwise 15 %.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    sleep_h = rng.uniform(4.5, 8.5, n_days)
    start = dates - pd.Timedelta(hours=1)  # 23:00 the evening before
    nights = pd.DataFrame(
        {
            "end": start + pd.to_timedelta(sleep_h, unit="h"),
            "sleep_type": "stages",
            **{c: np.nan for c in C.NIGHT_COLS},
        },
        index=dates,
    )
    nights["sleep_h"] = sleep_h
    nights["time_in_bed_h"] = sleep_h + 0.5
    nights["bedtime_h"] = 5.0
    nights["wake_pct"] = rng.uniform(5, 15, n_days)
    nights["rem_pct"] = rng.uniform(15, 25, n_days)
    nights["hr_sleep_mean"] = rng.uniform(50, 60, n_days)
    days = pd.DataFrame(
        {
            "steps": rng.uniform(4000, 14000, n_days),
            "lightly": rng.uniform(150, 300, n_days),
            "moderately": 10.0,
            "very": 10.0,
            "sedentary": 600.0,
            "z_cardio_peak": 0.0,
            "mvpa": rng.uniform(0, 80, n_days),
            "wear_min": 1400.0,
            "wear_day": 1000.0,
        },
        index=dates,
    )
    bad = rng.random(n_days) < np.where(effect & (sleep_h < 6), 0.7, 0.15)
    mood = np.where(bad, 2, rng.choice([3, 4], n_days))
    surveys = pd.DataFrame(
        {
            # 08:00 Oslo time = 07:00 UTC in winter
            "ts_utc": (dates + pd.Timedelta(hours=7)).tz_localize("UTC"),
            "mood": mood,
            "fatigue": mood,
            "stress": mood,
        }
    )
    return UserData("u1", nights, days, surveys)


def test_wilson_lower_penalises_small_samples() -> None:
    small = engine.wilson_lower(np.array([3.0]), np.array([3.0]))[0]
    large = engine.wilson_lower(np.array([10.0]), np.array([13.0]))[0]
    assert small < large


def test_support_and_cover_rules() -> None:
    n = 40
    ins = np.zeros((3, n), bool)
    ins[0, :5] = True  # too few days in the condition
    ins[1, :25] = True  # covers more than half of the days
    ins[2, :15] = True  # fine
    y = np.zeros(n, bool)
    y[:10] = True
    sc = engine.scores(ins, np.ones((3, n), bool), y)
    assert np.isneginf(sc[0]) and np.isneginf(sc[1]) and np.isfinite(sc[2])


def test_planted_sleep_effect_is_found() -> None:
    result = analyze_user(synthetic_user(effect=True))

    best = result["patterns"]["bad"]["patterns"][0]
    assert result["patterns"]["bad"]["status"] == "ok"
    assert best["feature"] == "sleep_h" and best["op"] == "below"
    assert 5.5 <= best["threshold"] <= 6.5


def test_no_effect_no_significant_pattern() -> None:
    result = analyze_user(synthetic_user(effect=False, seed=3))

    assert result["patterns"]["bad"]["status"] in ("not_enough_evidence", "preliminary")


def test_deterministic() -> None:
    assert analyze_user(synthetic_user()) == analyze_user(synthetic_user())


def test_new_user_is_collecting_data() -> None:
    result = analyze_user(synthetic_user(n_days=20))

    assert result["info"]["included"] is False
    assert result["info"]["exclusion_reasons"] == ["insufficient_days"]
    assert result["patterns"]["bad"] == {"status": "insufficient_days", "patterns": []}
    assert len(result["days"]) == 20  # the calendar still shows labelled days


def test_reasons_only_from_patterns_and_compare_limits() -> None:
    result = analyze_user(synthetic_user())
    pattern_cols = {p["column"] for p in result["patterns"]["bad"]["patterns"]}
    for day in result["days"]:
        assert len(day["reasons"]) <= C.MAX_REASONS and len(day["compare"]) <= C.COMPARE_MAX
        if day["label"] == "bad":
            assert {r["column"] for r in day["reasons"]} <= pattern_cols
            assert (day["no_reason_text"] is None) == bool(day["reasons"])
        if day["label"] == "neutral":
            assert day["reasons"] == []
        assert all(abs(c["z"]) >= C.COMPARE_MIN_Z for c in day["compare"])


def test_survey_after_midnight_belongs_to_previous_day() -> None:
    surveys = pd.DataFrame(
        {
            "ts_utc": pd.to_datetime(["2024-01-02 01:30", "2024-01-02 08:00"]).tz_localize("UTC"),
            "mood": [2, 4],
            "fatigue": [2, 4],
            "stress": [2, 4],
        }
    )
    by_day = cleaning.surveys_by_day(surveys)  # 02:30 Oslo -> evening of Jan 1

    assert list(by_day.date.dt.strftime("%Y-%m-%d")) == ["2024-01-01", "2024-01-02"]


def test_late_sleep_is_not_used_for_that_day() -> None:
    user = synthetic_user(n_days=5)
    user.nights.loc[user.nights.index[2], "end"] = user.nights.index[2] + pd.Timedelta(hours=11)
    table = cleaning.align(user)

    assert table.sleep_after_survey.iloc[2]
    assert np.isnan(table.sleep_h_lag1.iloc[2])


def test_nonwear_day_has_no_activity() -> None:
    user = synthetic_user(n_days=5)
    user.days.loc[user.days.index[1], "wear_day"] = 300  # watch on for 5 h only
    table = cleaning.align(user)

    assert np.isnan(table.steps_lag1.iloc[2])  # day 2 uses activity of day 1


@pytest.mark.parametrize("main_key", ["mainSleep", "isMainSleep"])
def test_fitbit_sleep_log_export_and_api_format(main_key: str) -> None:
    entry = {
        "logId": 1,
        main_key: True,
        "dateOfSleep": "2024-01-02",
        "startTime": "2024-01-01T23:00:00.000",
        "endTime": "2024-01-02T07:00:00.000",
        "minutesAsleep": 420,
        "minutesAwake": 60,
        "timeInBed": 480,
        "efficiency": 95,
        "type": "stages",
        "levels": {"summary": {"rem": {"minutes": 84}, "deep": {"minutes": 63}}},
    }
    nights = fitbit.nights([entry, entry], pd.DataFrame(), pd.Series(dtype=float))

    assert len(nights) == 1  # duplicate logId dropped
    row = nights.iloc[0]
    assert row.sleep_h == 7 and row.wake_pct == 12.5 and row.rem_pct == 20
    assert row.bedtime_h == 5  # 23:00 = 5 h after 18:00


def test_wear_and_minutes() -> None:
    ts = pd.date_range("2024-01-01 05:58", periods=4, freq="min")
    readings = pd.DataFrame({"ts": ts, "bpm": [60, 61, 250, 62], "confidence": [1, 0, 1, 2]})
    wear, hr = fitbit.wear_and_minutes(readings)

    assert wear.loc["2024-01-01", "wear_min"] == 4 and wear.loc["2024-01-01", "wear_day"] == 2
    assert list(hr) == [60.0, 62.0]  # confidence 0 and 250 bpm dropped
