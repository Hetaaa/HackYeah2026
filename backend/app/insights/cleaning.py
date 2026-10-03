"""Daily table for one user: one row per survey day D, features known before the survey.

night features -> main sleep ending on the morning of D (lag1), nights D, D-1, D-2 (avg3)
day features   -> calendar day D-1 (lag1), days D-1..D-3 (avg3); avg3 needs >= 2 of 3 values
a night that ended > survey + 60 min is not available: lag1 = NaN, avg3 from D-1, D-2
activity of a day worn < 12 h between 06:00 and 24:00 is NaN
"""

import warnings

import numpy as np
import pandas as pd

from app.insights import config as C
from app.insights.user import UserData


def _lagged(series: pd.Series, dates: pd.Series, offsets: list[int], min_n: int) -> np.ndarray:
    """Mean of `series` at dates - offset days; NaN if fewer than min_n values."""
    vals = np.column_stack(
        [series.reindex(dates - pd.Timedelta(days=o)).to_numpy(float) for o in offsets]
    )
    n = np.sum(~np.isnan(vals), axis=1)
    with warnings.catch_warnings():  # all-NaN rows are expected (no data) and become NaN
        warnings.simplefilter("ignore", RuntimeWarning)
        m = np.nanmean(vals, axis=1) if len(dates) else np.zeros(0)
    m[n < min_n] = np.nan
    return m


def surveys_by_day(surveys: pd.DataFrame) -> pd.DataFrame:
    """First check-in per local day; 00:00-04:59 = previous evening; invalid 0 -> NaN."""
    w = surveys.copy()
    ts = pd.to_datetime(w.ts_utc, utc=True).dt.tz_convert(C.TZ).dt.tz_localize(None)
    w["ts_local"] = ts
    if "date" in w:  # in-app survey: the user picked the day it describes
        w["date"] = pd.to_datetime(w.date)
        w["night_report"] = False
    else:  # timestamp only (PMData): 00:00-04:59 = previous evening
        w["night_report"] = (ts.dt.hour + ts.dt.minute / 60) < C.NIGHT_REPORT_END_H
        w["date"] = ts.dt.normalize() - pd.to_timedelta(w.night_report.astype(int), unit="D")
    for c in C.SURVEY_RAW:
        if c not in w:
            w[c] = np.nan
    for c in C.SCALE15:
        w[c] = w[c].where(w[c].between(1, 5))
    w["sleep_duration_h"] = w.sleep_duration_h.where(w.sleep_duration_h > 0)
    # a same-day daytime report wins over a late-night report reassigned to that day
    w = w.sort_values(["date", "night_report", "ts_local"], kind="stable")
    return w.groupby("date").head(1).reset_index(drop=True)


def activity(days: pd.DataFrame) -> pd.DataFrame:
    df = days.copy()
    df.loc[df.wear_day < C.WEAR_DAY_MIN, C.DAY_COLS] = np.nan
    df.loc[df.wear_min < C.SED_WEAR_MIN, "sedentary"] = np.nan
    lo, hi = C.VALID["steps"]
    df["steps"] = df.steps.where(df.steps.between(lo, hi))
    return df


def align(
    user: UserData, window_end: pd.Timestamp | None = None, all_dates: bool = False
) -> pd.DataFrame:
    """all_dates: one row for every date with any data (calendar), not only survey days."""
    first = surveys_by_day(user.surveys)
    if all_dates:
        dates = pd.DatetimeIndex(first.date).union(user.nights.index).union(user.days.index)
        first = pd.DataFrame({"date": dates}).merge(first, on="date", how="left")
        first["night_report"] = first.night_report.fillna(False).astype(bool)
    d = first.date
    nights, days = user.nights, activity(user.days)
    out = first[["date", "ts_local", "night_report", *C.SURVEY_RAW]].copy()
    out.insert(0, "user_id", user.user_id)
    out["weekday"] = d.dt.dayofweek
    end_d = pd.to_datetime(nights.end).reindex(d).reset_index(drop=True)
    late = (end_d > out.ts_local + pd.Timedelta(minutes=C.SLEEP_END_TOL_MIN)).fillna(False)
    late = late.to_numpy(bool)
    out["sleep_after_survey"] = late
    out["sleep_type"] = nights.sleep_type.reindex(d).to_numpy()
    for name in C.NIGHT_COLS:
        s = pd.to_numeric(nights[name], errors="coerce")
        out[f"{name}_lag1"] = _lagged(s, d, [0], 1)
        out.loc[late, f"{name}_lag1"] = np.nan
        if "avg3" in C.FEATURES[name].variants:
            avg = _lagged(s, d, [0, 1, 2], 2)
            avg[late] = _lagged(s, d, [1, 2], 2)[late]
            out[f"{name}_avg3"] = avg
    for name in C.DAY_COLS:
        out[f"{name}_lag1"] = _lagged(days[name], d, [1], 1)
        if "avg3" in C.FEATURES[name].variants:
            out[f"{name}_avg3"] = _lagged(days[name], d, [1, 2, 3], 2)
    wear_dm1 = days.wear_day.reindex(d - pd.Timedelta(days=1)).fillna(0).to_numpy()
    out["nonwear_dm1"] = wear_dm1 < C.WEAR_DAY_MIN
    # days on/after window_end are shown in the calendar but not used to find patterns or fit the
    # label (PMData demo: COVID lockdown from 2020-03-12; real users: no window_end)
    out["outside_window"] = d >= window_end if window_end is not None else False
    out["weekend_dm1"] = (d - pd.Timedelta(days=1)).dt.dayofweek >= 5
    return out


def add_label(df: pd.DataFrame) -> dict:
    """Median-centred composite of mood/fatigue/stress, fitted on in-window days (in place).

    With fewer than MIN_LABEL_DAYS check-ins, or identical answers every day, there is no personal
    baseline: the label falls back to the plain mean of the three answers (_absolute_label).
    """
    ok = df[C.LABEL_FIELDS].notna().all(axis=1)
    fit = ok & ~df.outside_window
    params: dict = {"label_source": "personal"}
    if fit.sum() < C.MIN_LABEL_DAYS:
        return _absolute_label(df, ok)
    dev = pd.DataFrame(index=df.index)
    for f in C.LABEL_FIELDS:
        med = float(df.loc[fit, f].median()) if fit.any() else np.nan
        sd = float(df.loc[fit, f].std(ddof=0)) if fit.any() else np.nan
        dev[f] = (df[f] - med) / sd if sd and sd > 0 else df[f] * 0.0
        params[f] = {"median": med, "sd": sd}
    comp = dev.mean(axis=1).where(ok)
    comp_sd = float(comp[fit].std(ddof=0)) if fit.any() else np.nan
    if not comp_sd > 0:  # identical answers every day: no personal spread to measure against
        return _absolute_label(df, ok)
    z = comp / comp_sd
    df["comp"] = comp
    df["z"] = z
    label = np.select([z < -C.DEAD_ZONE, z > C.DEAD_ZONE], ["bad", "good"], "neutral")
    df["label"] = pd.Series(label, index=df.index).where(z.notna())
    params["comp_sd"] = comp_sd
    raw = df.loc[ok, C.LABEL_FIELDS].mean(axis=1)
    params["raw_sd"] = float(raw.std(ddof=0)) if ok.any() else np.nan
    return params


def _absolute_label(df: pd.DataFrame, ok: pd.Series) -> dict:
    """No personal baseline: mean of the 3 answers, >= 3.5 good, <= 2.5 bad, score = mean - 3."""
    mean = df[C.LABEL_FIELDS].mean(axis=1).where(ok)
    df["comp"] = mean
    df["z"] = mean - 3
    label = np.select([mean >= 3.5, mean <= 2.5], ["good", "bad"], "neutral")
    df["label"] = pd.Series(label, index=df.index).where(ok)
    raw_sd = float(mean[ok].std(ddof=0)) if ok.sum() > 1 else np.nan
    return {"label_source": "absolute", "raw_sd": raw_sd, "comp_sd": np.nan}


def build_table(
    user: UserData, window_end: pd.Timestamp | None = None, all_dates: bool = False
) -> tuple[pd.DataFrame, dict]:
    """Aligned + labelled daily table and gate info for one user."""
    df = align(user, window_end, all_dates)
    label = add_label(df)
    full = df.label.notna() & df.sleep_h_lag1.notna() & df.steps_lag1.notna()
    df["in_analysis_window"] = full & ~df.outside_window
    win = df[df.in_analysis_window]
    n_bad, n_good = int((win.label == "bad").sum()), int((win.label == "good").sum())
    reasons = []  # most actionable first: a new user is collecting data, not "too uniform"
    if full.sum() < C.MIN_FULL_DAYS:
        reasons.append("insufficient_days")
    if not label["raw_sd"] >= C.MIN_RAW_SD:
        reasons.append("insufficient_variation")
    hrz_days = int((win.z_cardio_peak_lag1 > C.E_HRZ_MIN_MIN).sum())
    info = {
        "included": not reasons,
        "exclusion_reasons": reasons,
        "label": label,
        "n_bad_window": n_bad,
        "n_good_window": n_good,
        "bad_patterns_enabled": n_bad >= C.MIN_BAD_DAYS,
        "good_patterns_enabled": n_good >= C.MIN_GOOD_DAYS,
        "group_e_feature": "z_cardio_peak" if hrz_days >= C.E_HRZ_MIN_DAYS else "mvpa",
        "n_surveys": len(user.surveys),
        "n_days": int(df.label.notna().sum()),
        "n_full_days": int(full.sum()),
        "n_full_days_needed": C.MIN_FULL_DAYS,
        "label_source": label["label_source"],
        "classic_nights": int((user.nights.sleep_type == "classic").sum()),
    }
    return df, info
