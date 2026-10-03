"""Data source for the API: rows of the Day table (one dict per day) -> UserData.

Field names are those of app.models.Day. Night fields belong to the sleep that ended on the
morning of `date`, activity fields to the calendar day `date`. Missing wear time = assume worn.
"""

import numpy as np
import pandas as pd

from app.insights import config as C
from app.insights.user import UserData

NIGHT = {  # nights column -> Day field
    "wake_pct": "wake_pct",
    "rem_pct": "rem_pct",
    "deep_pct": "deep_pct",
    "hr_sleep_mean": "sleep_hr_mean",
    "sleep_eff": "sleep_efficiency",
    "rhr_night": "resting_hr",
    "wake_min": "wake_minutes",
    "ss_overall": "sleep_score",
}
ACTIVITY = {  # days column -> Day field
    "steps": "steps",
    "mvpa": "active_minutes",
    "lightly": "light_minutes",
    "sedentary": "sedentary_minutes",
    "z_cardio_peak": "cardio_peak_minutes",
}
SURVEY = ["mood", "fatigue", "stress", "sleep_quality"]
DEFAULT_SURVEY_HOUR = 8  # survey time unknown -> assume a morning check-in


def _num(rows: pd.DataFrame, field: str) -> pd.Series:
    return pd.to_numeric(rows.get(field, pd.Series(np.nan, index=rows.index)), errors="coerce")


def user_from_rows(user_id: str, rows: list[dict]) -> UserData:
    df = pd.DataFrame(rows, columns=sorted({k for r in rows for k in r} | {"date"}))
    df["date"] = pd.to_datetime(df.date)
    df = df.drop_duplicates("date", keep="last").set_index("date").sort_index()

    has_night = _num(df, "sleep_minutes").notna()
    n = df[has_night]
    nights = pd.DataFrame(index=n.index)
    nights["end"] = pd.to_datetime(n.get("sleep_end"), format="ISO8601")
    nights["sleep_type"] = n.get("sleep_type")
    nights["sleep_h"] = _num(n, "sleep_minutes") / 60
    nights["time_in_bed_h"] = _num(n, "time_in_bed_minutes") / 60
    start = pd.to_datetime(n.get("sleep_start"), format="ISO8601")
    nights["bedtime_h"] = (start - (n.index - pd.Timedelta(hours=6))).dt.total_seconds() / 3600
    for col, field in NIGHT.items():
        nights[col] = _num(n, field)
    stages = nights.sleep_type == "stages"
    nights.loc[~stages, ["wake_pct", "rem_pct", "deep_pct"]] = np.nan
    for col, (lo, hi) in C.VALID.items():
        if col in nights:
            nights[col] = nights[col].where(nights[col].between(lo, hi))

    days = pd.DataFrame(index=df.index)
    for col, field in ACTIVITY.items():
        days[col] = _num(df, field)
    days["wear_min"] = _num(df, "wear_minutes").fillna(24 * 60)
    days["wear_day"] = _num(df, "wear_minutes_day").fillna(18 * 60)

    s = df[df[SURVEY[:3]].notna().any(axis=1)] if set(SURVEY[:3]) <= set(df) else df.iloc[:0]
    local_8am = (s.index + pd.Timedelta(hours=DEFAULT_SURVEY_HOUR)).tz_localize(C.TZ)
    ts = pd.Series(local_8am.tz_convert("UTC"), index=s.index)
    if "survey_at" in s:
        ts = pd.to_datetime(s.survey_at, utc=True, format="ISO8601").fillna(ts)
    surveys = pd.DataFrame({"date": s.index, "ts_utc": ts.to_numpy()})
    for f in SURVEY:
        surveys[f] = _num(s, f).to_numpy()
    return UserData(user_id, nights.rename_axis("date"), days.rename_axis("date"), surveys)
