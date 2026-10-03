"""Demo data source: PMData files (Fitbit export + PMSys wellness) -> UserData.

Only demo users come from files; real users come from watch sync + the in-app survey.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from app.insights import fitbit
from app.insights.user import UserData

PIDS = [f"p{i:02d}" for i in range(1, 17)]
HR_PAT = re.compile(
    rb'"dateTime": "(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)", "value": \{"bpm": (\d+), '
    rb'"confidence": (-?\d)\}'
)


def _json(root: Path, pid: str, name: str) -> list:
    path = root / pid / "fitbit" / name
    return json.loads(path.read_text()) if path.exists() else []


def _readings(root: Path, pid: str) -> pd.DataFrame:
    """heart_rate.json is ~120 MB: regex over bytes instead of json.load keeps memory low."""
    path = root / pid / "fitbit" / "heart_rate.json"
    if not path.exists():
        return pd.DataFrame(columns=["ts", "bpm", "confidence"])
    a = np.array(HR_PAT.findall(path.read_bytes()), dtype=object)
    return pd.DataFrame(
        {
            "ts": pd.to_datetime(pd.Series(a[:, 0]).str.decode("ascii")),
            "bpm": a[:, 1].astype(int),
            "confidence": a[:, 2].astype(int),
        }
    )


def _heart_rate(root: Path, pid: str, cache: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Wear per day + per-minute HR, cached per participant (the scan is the slow part)."""
    cache.mkdir(parents=True, exist_ok=True)
    wear_path, hr_path = cache / f"{pid}_wear.csv", cache / f"{pid}_hr.csv"
    if not (wear_path.exists() and hr_path.exists()):
        wear, hr = fitbit.wear_and_minutes(_readings(root, pid))
        wear.rename_axis("date").to_csv(wear_path)
        hr.rename("bpm").rename_axis("ts").to_csv(hr_path)
    wear = pd.read_csv(wear_path, parse_dates=["date"], index_col="date")
    hr = pd.read_csv(hr_path, parse_dates=["ts"], index_col="ts").bpm
    return wear, hr


def _sleep_scores(root: Path, pid: str) -> pd.DataFrame:
    path = root / pid / "fitbit" / "sleep_score.csv"
    if not path.exists():
        return pd.DataFrame(columns=["logId", "rhr_night", "ss_overall"])
    ss = pd.read_csv(path)
    return ss.rename(
        columns={
            "sleep_log_entry_id": "logId",
            "resting_heart_rate": "rhr_night",
            "overall_score": "ss_overall",
        }
    )[["logId", "rhr_night", "ss_overall"]]


def _surveys(root: Path, pid: str) -> pd.DataFrame:
    w = pd.read_csv(root / pid / "pmsys" / "wellness.csv")
    w["ts_utc"] = pd.to_datetime(w.effective_time_frame, utc=True)
    return w.drop(columns=["effective_time_frame", "soreness_area"])


def load_user(root: Path, pid: str, cache: Path) -> UserData:
    wear, hr = _heart_rate(root, pid, cache)
    return UserData(
        user_id=pid,
        nights=fitbit.nights(_json(root, pid, "sleep.json"), _sleep_scores(root, pid), hr),
        days=fitbit.days(
            steps=fitbit.daily_values(_json(root, pid, "steps.json")),
            lightly=fitbit.daily_values(_json(root, pid, "lightly_active_minutes.json")),
            moderately=fitbit.daily_values(_json(root, pid, "moderately_active_minutes.json")),
            very=fitbit.daily_values(_json(root, pid, "very_active_minutes.json")),
            sedentary=fitbit.daily_values(_json(root, pid, "sedentary_minutes.json")),
            zones=fitbit.cardio_peak(_json(root, pid, "time_in_heart_rate_zones.json")),
            wear=wear,
        ),
        surveys=_surveys(root, pid),
    )
