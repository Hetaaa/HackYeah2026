"""The API data path: Day rows -> UserData (app/insights/sources/rows.py)."""

import datetime as dt

import numpy as np
import pandas as pd

from app.insights import cleaning
from app.insights.sources.rows import user_from_rows


def row(day: int, **fields: object) -> dict:
    return {"user_id": "u", "date": dt.date(2024, 1, day), **fields}


def test_empty_user() -> None:
    user = user_from_rows("u", [])

    assert user.nights.empty and user.days.empty and user.surveys.empty
    assert cleaning.align(user, all_dates=True).empty


def test_missing_survey_time_defaults_to_8am_local() -> None:
    user = user_from_rows("u", [row(15, mood=3, fatigue=3, stress=3)])

    assert user.surveys.ts_utc.iloc[0] == pd.Timestamp("2024-01-15 07:00", tz="UTC")


def test_naive_survey_time_is_utc() -> None:
    at = dt.datetime(2024, 1, 15, 6, 30)  # SQLite drops tzinfo
    user = user_from_rows("u", [row(15, mood=3, fatigue=3, stress=3, survey_at=at)])

    assert user.surveys.ts_utc.iloc[0] == pd.Timestamp("2024-01-15 06:30", tz="UTC")


def test_bedtime_and_stage_fields() -> None:
    night = {
        "sleep_minutes": 420,
        "sleep_start": dt.datetime(2024, 1, 14, 23, 30),
        "sleep_end": dt.datetime(2024, 1, 15, 7, 0),
        "wake_pct": 10,
        "rem_pct": 20,
    }
    user = user_from_rows(
        "u",
        [
            row(15, sleep_type="stages", **night),
            row(16, sleep_type="classic", **night),
            row(17, sleep_type=None, **night),
        ],
    )
    n = user.nights

    assert n.loc["2024-01-15", "bedtime_h"] == 5.5  # 23:30 = 5.5 h after 18:00
    assert n.loc["2024-01-15", "wake_pct"] == 10
    assert np.isnan(n.loc["2024-01-16", "wake_pct"])  # classic nights have no stages
    assert n.loc["2024-01-17", "rem_pct"] == 20  # unknown type keeps the values
    assert np.isnan(n.loc["2024-01-16", "bedtime_h"])  # start on 14 Jan is 2 days early


def test_unknown_wear_counts_as_worn() -> None:
    user = user_from_rows("u", [row(15, steps=8000)])

    assert user.days.loc["2024-01-15", "wear_day"] == 18 * 60
