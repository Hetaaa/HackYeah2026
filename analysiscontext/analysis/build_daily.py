"""Build the joined daily table for PMData (base for cleaning / backend pipeline).

Outputs (analysis/cache/):
  survey.csv        one row per wellness report (all reports, local time, flags)
  fitbit_day.csv    one row per pid x calendar day (activity, RHR, wear) - local calendar day
  sleep_night.csv   one row per pid x dateOfSleep (main sleep, longest if several)
  daily.csv         one row per pid x survey day D, features aligned to "available before survey":
                       sleep/night features  -> night ending morning D   (lag1), nights D, D-1, D-2 (avg3)
                       activity / RHR / sRPE -> calendar day D-1         (lag1), days D-1..D-3 (avg3)
                       rhr_night             -> sleep_score RHR of night ending D
                    avg3 requires >= 2 of 3 non-null values.

Conventions:
  * wellness effective_time_frame is UTC -> Europe/Oslo; first report per local day kept.
  * Fitbit timestamps are local (sleep_score.csv 'Z' suffix is fake: equals sleep endTime local).
  * 0 on 1-5 survey scales -> NaN (invalid). readiness 0 kept (valid on 0-10) but flagged.
  * resting HR == 0 -> NaN.
  * Non-wear days (daytime wear 06-24 < WEAR_DAY_MIN=720) -> activity features NaN before lags.
  * sedentary additionally NaN when total wear < SED_WEAR_MIN=1200 (unworn time is counted as sedentary).

Usage: uv run --with pandas --with numpy --with pyarrow python build_daily.py [--wear-day-min 720]
"""
from __future__ import annotations

import argparse
import warnings
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "pmdata"
CACHE = HERE / "cache"
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", message=".*Sorting by default.*")
PIDS = [f"p{i:02d}" for i in range(1, 17)]
TZ = "Europe/Oslo"

SCALE15 = ["fatigue", "mood", "sleep_quality", "soreness", "stress"]
SURVEY_FIELDS = ["fatigue", "mood", "readiness", "sleep_duration_h", "sleep_quality", "soreness", "stress"]

# activity features that are invalid on non-wear days
ACT_COLS = ["steps", "distance_km", "calories", "lightly", "moderately", "very", "mvpa", "active_total",
            "sedentary", "rhr_day"]
SLEEP_COLS = ["sleep_h", "sleep_eff", "bedtime_h", "wake_h", "time_in_bed_h", "rhr_night"]
LOAD_COLS = ["srpe_load", "ex_min", "ex_min_nonwalk"]
DEFAULT_WEAR_DAY_MIN = 720  # min of HR-wear between 06:00-24:00 (of 1080); see analiza-pmdata.md sec. 5
SED_WEAR_MIN = 1200  # sedentary trusted only with >= 20 h total wear
NIGHT_REPORT_END_H = 5  # reports before 05:00 local belong to the previous day
MIN_SLEEP_MIN = 120  # main sleep shorter than 2 h = artefact
SLEEP_END_TOL_MIN = 60  # sleep must end <= survey time + 60 min to count as 'before survey'


# ---------------------------------------------------------------- loaders
def _fb(pid, name):
    p = ROOT / pid / "fitbit" / name
    return json.load(open(p)) if p.exists() else None


def load_survey(pid: str) -> pd.DataFrame:
    w = pd.read_csv(ROOT / pid / "pmsys" / "wellness.csv")
    ts = pd.to_datetime(w.effective_time_frame, utc=True).dt.tz_convert(TZ)
    w["ts_local"] = ts.dt.tz_localize(None)
    w["date_cal"] = ts.dt.tz_localize(None).dt.normalize()
    w["hour"] = ts.dt.hour + ts.dt.minute / 60
    # 00:00-04:59 = late-evening report of the previous day
    w["night_report"] = w.hour < NIGHT_REPORT_END_H
    w["date"] = w.date_cal - pd.to_timedelta(w.night_report.astype(int), unit="D")
    w["readiness_zero"] = w.readiness == 0
    for c in SCALE15:
        w[c] = w[c].where(w[c].between(1, 5))
    w["sleep_duration_h"] = w.sleep_duration_h.where(w.sleep_duration_h > 0)
    w = w.sort_values(["date", "night_report", "ts_local"])  # same-day daytime report wins over a reassigned one
    w["n_reports_day"] = w.groupby("date").date.transform("size")
    w["rank_in_day"] = w.groupby("date").cumcount()
    w.insert(0, "pid", pid)
    return w.drop(columns=["soreness_area", "effective_time_frame"])


def _minute_daily_sum(pid, name, col, scale=1.0):
    d = _fb(pid, name)
    if d is None:
        return pd.Series(dtype=float, name=col)
    df = pd.DataFrame(d)
    df["date"] = pd.to_datetime(df.dateTime.str[:10])
    df["value"] = pd.to_numeric(df.value) * scale
    s = df.groupby("date").value.sum()
    s.name = col
    return s


def _daily_series(pid, name, col):
    d = _fb(pid, name)
    if d is None:
        return pd.Series(dtype=float, name=col)
    df = pd.DataFrame(d)
    df["date"] = pd.to_datetime(df.dateTime.str[:10])
    if isinstance(df.value.iloc[0], dict):
        df["value"] = df.value.map(lambda v: v.get("value"))
    s = pd.to_numeric(df.value).groupby(df.date).first()
    s.name = col
    return s


def load_fitbit_day(pid: str, wear: pd.DataFrame | None) -> pd.DataFrame:
    parts = [
        _minute_daily_sum(pid, "steps.json", "steps"),
        _minute_daily_sum(pid, "distance.json", "distance_km", 1e-5),  # cm -> km
        _minute_daily_sum(pid, "calories.json", "calories"),
        _daily_series(pid, "lightly_active_minutes.json", "lightly"),
        _daily_series(pid, "moderately_active_minutes.json", "moderately"),
        _daily_series(pid, "very_active_minutes.json", "very"),
        _daily_series(pid, "sedentary_minutes.json", "sedentary"),
        _daily_series(pid, "resting_heart_rate.json", "rhr_day"),
    ]
    df = pd.concat(parts, axis=1)
    df.index.name = "date"
    df["rhr_day"] = df.rhr_day.where(df.rhr_day > 0)
    df["mvpa"] = df.moderately + df.very
    df["active_total"] = df.lightly + df.mvpa
    df = df.join(load_load(pid), how="outer")
    if wear is not None:
        ww = wear[wear.pid == pid].assign(date=lambda x: pd.to_datetime(x.date)).set_index("date")
        df = df.join(ww[["wear_min", "wear_min_night"]], how="left")
        df["wear_min"] = df.wear_min.fillna(0)
        df["wear_min_night"] = df.wear_min_night.fillna(0)
        df["wear_day"] = df.wear_min - df.wear_min_night
    df = df.reset_index()
    df.insert(0, "pid", pid)
    return df


def load_load(pid: str) -> pd.DataFrame:
    """Training load per local calendar day: sRPE (RPE x min) and Fitbit exercise minutes."""
    sr = pd.read_csv(ROOT / pid / "pmsys" / "srpe.csv")
    sr["date"] = (pd.to_datetime(sr.end_date_time, utc=True).dt.tz_convert(TZ)
                  .dt.tz_localize(None).dt.normalize())
    sr["load"] = sr.perceived_exertion * sr.duration_min
    a = sr.groupby("date").load.sum(min_count=1).rename("srpe_load")
    ex = _fb(pid, "exercise.json") or []
    e = pd.DataFrame([dict(date=x["startTime"][:10], name=x["activityName"],
                           minutes=x.get("activeDuration", x.get("duration", 0)) / 60000) for x in ex])
    if len(e):
        e["date"] = pd.to_datetime(e.date)
        b = e.groupby("date").minutes.sum().rename("ex_min")
        c = e[e.name != "Walk"].groupby("date").minutes.sum().rename("ex_min_nonwalk")
    else:
        b = pd.Series(dtype=float, name="ex_min")
        c = pd.Series(dtype=float, name="ex_min_nonwalk")
    out = pd.concat([a, b, c], axis=1)
    out.index.name = "date"
    return out


def load_sleep(pid: str) -> pd.DataFrame:
    s = _fb(pid, "sleep.json") or []
    rows = []
    for e in s:
        if not e.get("mainSleep"):
            continue
        st = pd.Timestamp(e["startTime"].replace("T", " "))
        en = pd.Timestamp(e["endTime"].replace("T", " "))
        rows.append(dict(logId=e["logId"], date=pd.Timestamp(e["dateOfSleep"]), start=st, end=en,
                         minutesAsleep=e["minutesAsleep"], timeInBed=e["timeInBed"],
                         efficiency=e["efficiency"], type=e["type"]))
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["pid", "date"] + SLEEP_COLS)
    # validity: night must start 18:00 (D-1) .. 12:00 (D), last >= 2 h, efficiency > 0
    bt = (df.start - (df.date - pd.Timedelta(hours=6))).dt.total_seconds() / 3600
    df["valid_night"] = bt.between(0, 18) & (df.minutesAsleep >= MIN_SLEEP_MIN) & (df.efficiency > 0)
    df = df[df.valid_night]
    df["n_main_sleeps"] = df.groupby("date").date.transform("size")
    df = df.sort_values("minutesAsleep").groupby("date").tail(1)  # longest main sleep
    df["sleep_h"] = df.minutesAsleep / 60
    df["time_in_bed_h"] = df.timeInBed / 60
    df["sleep_eff"] = df.efficiency
    # hours since 18:00 of the previous evening relative to the wake date
    ref = df.date - pd.Timedelta(hours=6)
    df["bedtime_h"] = (df.start - ref).dt.total_seconds() / 3600
    df["wake_h"] = (df.end - df.date).dt.total_seconds() / 3600
    ss = pd.read_csv(ROOT / pid / "fitbit" / "sleep_score.csv")
    ss = ss[["sleep_log_entry_id", "resting_heart_rate", "overall_score"]].rename(
        columns={"sleep_log_entry_id": "logId", "resting_heart_rate": "rhr_night",
                 "overall_score": "sleep_score"})
    df = df.merge(ss, on="logId", how="left")
    df["rhr_night"] = df.rhr_night.where(df.rhr_night > 0)
    df.insert(0, "pid", pid)
    return df[["pid", "date", "logId", "start", "end", "type", "n_main_sleeps", "sleep_score"] + SLEEP_COLS]


# ---------------------------------------------------------------- lags
def _lagged(series: pd.Series, dates: pd.Series, offsets: list[int], min_n: int):
    """Mean of series at dates-offset days; NaN if fewer than min_n values."""
    vals = np.column_stack([series.reindex(dates - pd.Timedelta(days=o)).to_numpy() for o in offsets])
    n = np.sum(~np.isnan(vals), axis=1)
    with np.errstate(all="ignore"):
        m = np.nanmean(vals, axis=1)
    m[n < min_n] = np.nan
    return m


def build(wear_day_min: int = DEFAULT_WEAR_DAY_MIN, write: bool = True):
    wear_path = CACHE / "wear_minutes.csv"
    wear = pd.read_csv(wear_path) if wear_path.exists() else None
    surveys, days, nights, daily = [], [], [], []
    for pid in PIDS:
        sv = load_survey(pid)
        fd = load_fitbit_day(pid, wear)
        sl = load_sleep(pid)
        surveys.append(sv)
        days.append(fd)
        nights.append(sl)

        fdi = fd.set_index("date")
        nonwear = fdi.wear_day < wear_day_min
        act = fdi[ACT_COLS].copy()
        act.loc[nonwear] = np.nan
        act.loc[fdi.wear_min < SED_WEAR_MIN, "sedentary"] = np.nan
        load = fdi[LOAD_COLS].copy()
        # training load: no session logged on a worn day = 0 (only within the logging period)
        sli = sl.set_index("date")

        first = sv[sv.rank_in_day == 0].copy()
        D = first.date.reset_index(drop=True)
        out = first.reset_index(drop=True)
        out["weekday"] = D.dt.dayofweek
        out["n_surveys_total"] = len(sv)
        out["wear_min_dm1"] = fdi.wear_min.reindex(D - pd.Timedelta(days=1)).to_numpy()
        out["wear_day_dm1"] = fdi.wear_day.reindex(D - pd.Timedelta(days=1)).fillna(0).to_numpy()
        out["sedentary_raw_dm1"] = fdi.sedentary.reindex(D - pd.Timedelta(days=1)).to_numpy()
        out["has_sleep"] = sli.sleep_h.reindex(D).notna().to_numpy()
        end_D = pd.to_datetime(sli.end).reindex(D).reset_index(drop=True)
        out["sleep_after_survey"] = (end_D > out.ts_local + pd.Timedelta(minutes=SLEEP_END_TOL_MIN)).to_numpy()
        for c in SLEEP_COLS:
            s = sli[c] if c in sli else pd.Series(dtype=float)
            out[f"{c}_lag1"] = _lagged(s, D, [0], 1)
            out[f"{c}_avg3"] = _lagged(s, D, [0, 1, 2], 2)
            # night ending D not finished before the survey -> not available
            out.loc[out.sleep_after_survey, f"{c}_lag1"] = np.nan
            prev = _lagged(s, D, [1, 2], 2)
            out.loc[out.sleep_after_survey, f"{c}_avg3"] = prev[out.sleep_after_survey.to_numpy()]
        for c in ACT_COLS:
            out[f"{c}_lag1"] = _lagged(act[c], D, [1], 1)
            out[f"{c}_avg3"] = _lagged(act[c], D, [1, 2, 3], 2)
        for c in LOAD_COLS:
            s = load[c]
            # fill 0 for days inside the person's logging span (no session = no load)
            if s.notna().any():
                span = pd.date_range(s.first_valid_index(), s.last_valid_index())
                s = s.reindex(span).fillna(0)
            out[f"{c}_lag1"] = _lagged(s, D, [1], 1)
            out[f"{c}_avg3"] = _lagged(s, D, [1, 2, 3], 2)
        out["nonwear_dm1"] = (out.wear_day_dm1 < wear_day_min).to_numpy()
        daily.append(out)

    sv = pd.concat(surveys, ignore_index=True)
    fd = pd.concat(days, ignore_index=True)
    sl = pd.concat(nights, ignore_index=True)
    dl = pd.concat(daily, ignore_index=True)
    if write:
        CACHE.mkdir(exist_ok=True)
        sv.to_csv(CACHE / "survey.csv", index=False)
        fd.to_csv(CACHE / "fitbit_day.csv", index=False)
        sl.to_csv(CACHE / "sleep_night.csv", index=False)
        dl.to_csv(CACHE / "daily.csv", index=False)
        print("wrote", CACHE, "survey", len(sv), "fitbit_day", len(fd), "sleep", len(sl), "daily", len(dl))
    return sv, fd, sl, dl


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wear-day-min", type=int, default=DEFAULT_WEAR_DAY_MIN)
    a = ap.parse_args()
    build(a.wear_day_min)
