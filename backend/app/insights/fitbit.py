"""Watch data adapter: Fitbit Web API payloads -> normalized per-user frames (no file IO here).

PMData files are exports of the same Fitbit API. The Fitbit Web API itself was turned down on
2026-09-30 (successor: Google Health API, a different format), so this parser now serves the
PMData demo and Fitbit data exports; see docs/watch-sources.md for live sources.
Another watch brand needs its own adapter producing the same frames (see UserData).

Normalized frames:
  readings  heart-rate samples: ts (local), bpm, confidence
  nights    index = wake date; end, sleep_type + C.NIGHT_COLS (main sleep, validated)
  days      index = local calendar date; C.DAY_COLS + wear_min, wear_day (raw, not yet filtered)
"""

import numpy as np
import pandas as pd

from app.insights import config as C


# ---------------------------------------------------------------- heart rate
def wear_and_minutes(readings: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """readings (ts, bpm, confidence) -> (wear per day: wear_min, wear_day 06-24), bpm/minute."""
    if readings.empty:
        return pd.DataFrame(columns=["wear_min", "wear_day"]), pd.Series(dtype=float)
    ts = pd.DatetimeIndex(readings.ts).floor("min")
    minutes = pd.Series(1, index=ts).groupby(level=0).first()  # distinct worn minutes
    day = minutes.index.normalize()
    night = minutes.index.hour < 6
    wear = pd.DataFrame({"wear_min": minutes.groupby(day).size()})
    wear["wear_day"] = wear.wear_min - minutes[night].groupby(day[night]).size().reindex(
        wear.index
    ).fillna(0)
    bpm, conf = readings.bpm.to_numpy(), readings.confidence.to_numpy()
    ok = (conf > 0) & (bpm >= 30) & (bpm <= 220)
    hr = pd.Series(bpm[ok], index=ts[ok]).groupby(level=0).mean().sort_index()
    return wear, hr.astype(float)


def _night_hr(hr: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Mean per-minute HR inside [start, end); NaN if < 50 % of sleep minutes are covered."""
    if hr.empty:
        return np.nan
    idx = hr.index.values
    i0, i1 = np.searchsorted(idx, np.datetime64(start)), np.searchsorted(idx, np.datetime64(end))
    duration = (end - start).total_seconds() / 60
    if i1 <= i0 or duration <= 0 or (i1 - i0) / duration < C.NIGHT_HR_MIN_COVER:
        return np.nan
    return float(hr.to_numpy()[i0:i1].mean())


# ---------------------------------------------------------------- sleep
def _levels(e: dict) -> dict:
    if e["type"] != "stages":
        return {"wake_pct": np.nan, "rem_pct": np.nan, "deep_pct": np.nan}
    sm = e.get("levels", {}).get("summary", {})
    asleep = e["minutesAsleep"]
    return {
        "wake_pct": 100 * e["minutesAwake"] / e["timeInBed"] if e["timeInBed"] else np.nan,
        "rem_pct": 100 * sm.get("rem", {}).get("minutes", np.nan) / asleep,
        "deep_pct": 100 * sm.get("deep", {}).get("minutes", np.nan) / asleep,
    }


def nights(sleep_log: list[dict], sleep_scores: pd.DataFrame, hr: pd.Series) -> pd.DataFrame:
    """sleep_log: Fitbit sleep log entries (API: isMainSleep, export: mainSleep).
    sleep_scores: columns logId, rhr_night, ss_overall (may be empty)."""
    rows: dict[int, dict] = {}
    for e in sleep_log:
        main = e.get("mainSleep", e.get("isMainSleep"))
        if main and e["logId"] not in rows:  # exports contain duplicate logIds
            rows[e["logId"]] = {
                "logId": e["logId"],
                "date": pd.Timestamp(e["dateOfSleep"]),
                "start": pd.Timestamp(e["startTime"].replace("T", " ")),
                "end": pd.Timestamp(e["endTime"].replace("T", " ")),
                "minutesAsleep": e["minutesAsleep"],
                "timeInBed": e["timeInBed"],
                "sleep_eff": e["efficiency"],
                "wake_min": e["minutesAwake"],
                "sleep_type": e["type"],
                **_levels(e),
            }
    cols = ["end", "sleep_type", *C.NIGHT_COLS]
    if not rows:
        return pd.DataFrame(columns=cols, index=pd.DatetimeIndex([], name="date"))
    df = pd.DataFrame(rows.values())
    # valid night: starts 18:00 (D-1) .. 12:00 (D), lasts >= 2 h, efficiency > 0
    since_18 = (df.start - (df.date - pd.Timedelta(hours=6))).dt.total_seconds() / 3600
    df = df[since_18.between(0, 18) & (df.minutesAsleep >= C.MIN_SLEEP_MIN) & (df.sleep_eff > 0)]
    df = df.sort_values("minutesAsleep", kind="stable").groupby("date").tail(1)  # longest
    df["sleep_h"] = df.minutesAsleep / 60
    df["time_in_bed_h"] = df.timeInBed / 60
    df["bedtime_h"] = (df.start - (df.date - pd.Timedelta(hours=6))).dt.total_seconds() / 3600
    scores = sleep_scores if len(sleep_scores) else pd.DataFrame(columns=["logId"])
    df = df.merge(scores.drop_duplicates("logId"), on="logId", how="left")
    for c in ("rhr_night", "ss_overall"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["hr_sleep_mean"] = [_night_hr(hr, s, e) for s, e in zip(df.start, df.end, strict=True)]
    for c, (lo, hi) in C.VALID.items():
        if c in df:
            df[c] = df[c].where(df[c].between(lo, hi))
    return df.set_index("date")[cols]


# ---------------------------------------------------------------- activity
def daily_values(entries: list[dict]) -> pd.Series:
    """[{dateTime, value}] (value may be {"value": x}) -> per-day series (sum of minute data)."""
    if not entries:
        return pd.Series(dtype=float)
    df = pd.DataFrame(entries)
    values = df.value.map(lambda v: v.get("value") if isinstance(v, dict) else v)
    return pd.to_numeric(values).groupby(pd.to_datetime(df.dateTime.str[:10])).sum()


def cardio_peak(zones: list[dict]) -> pd.Series:
    """time_in_heart_rate_zones entries -> minutes in cardio + peak zones per day."""
    if not zones:
        return pd.Series(dtype=float)
    s = pd.Series(
        [
            x["value"]["valuesInZones"].get("IN_DEFAULT_ZONE_2", np.nan)
            + x["value"]["valuesInZones"].get("IN_DEFAULT_ZONE_3", np.nan)
            for x in zones
        ],
        index=[pd.Timestamp(x["dateTime"][:10]) for x in zones],
    )
    return s.groupby(level=0).first()


def days(
    steps: pd.Series,
    lightly: pd.Series,
    moderately: pd.Series,
    very: pd.Series,
    sedentary: pd.Series,
    zones: pd.Series,
    wear: pd.DataFrame,
) -> pd.DataFrame:
    df = pd.concat(
        {
            "steps": steps,
            "lightly": lightly,
            "moderately": moderately,
            "very": very,
            "sedentary": sedentary,
            "z_cardio_peak": zones,
        },
        axis=1,
        sort=True,
    )
    df["mvpa"] = df.moderately + df.very
    df = df.join(wear, how="left")
    df["wear_min"] = df.wear_min.fillna(0)
    df["wear_day"] = df.wear_day.fillna(0)
    return df[[*C.DAY_COLS, "wear_min", "wear_day"]]
