"""Round 2: extra WATCH-ONLY features skipped in round 1.

Sources (pmdata/pXX/fitbit/ only):
  sleep.json levels      -> stage minutes / percentages, wake episodes (main sleep selected in round 1)
  sleep_score.csv        -> sub-scores, deep minutes, restlessness (join sleep_log_entry_id = logId)
  time_in_heart_rate_zones.json -> minutes per default HR zone per calendar day
  exercise.json          -> user-started (tracker/manual) exercise minutes, exercise avg HR, cardio+peak minutes
  heart_rate.json        -> nightly HR during main sleep, daytime HR (heavy: per participant, cached)

Alignment = round 1 (build_daily.py):
  night features  -> main sleep of the night ending on survey day D (same logId as cache/sleep_night.csv,
                     i.e. same validity rules), lag1 NaN when sleep ended > survey + 60 min,
                     avg3 = nights D, D-1, D-2 (>= 2 of 3; when lag1 unavailable: D-1, D-2 both required)
  day features    -> calendar day D-1, NaN when wear_day (06-24) < 720; avg3 = D-1..D-3 (>= 2 of 3)

Outputs (analysis/cache/, round-1 files untouched):
  extra_night.csv         pid x dateOfSleep  (selected main sleep) raw night features
  extra_day.csv           pid x calendar day raw day features (before wear filter, wear_day attached)
  hr_derived/<pid>.csv    per participant HR-derived night + day stats (cache of the heavy scan)
  extra_features.csv      pid x survey day D, *_lag1 / *_avg3

Usage: uv run --with pandas --with numpy python build_extra.py [--redo-hr]
"""
from __future__ import annotations

import json
import re
import sys
import warnings

import numpy as np
import pandas as pd

from HackYeah2026.analysiscontext.analysis.build_daily import CACHE, DEFAULT_WEAR_DAY_MIN, PIDS, ROOT, _fb, _lagged

warnings.filterwarnings("ignore")
HRDIR = CACHE / "hr_derived"
HR_PAT = re.compile(rb'"dateTime": "(\d{4}-\d\d-\d\d) (\d\d):(\d\d):(\d\d)", "value": \{"bpm": (\d+), '
                    rb'"confidence": (-?\d)\}')
NIGHT_HR_MIN_COVER = 0.5  # >= 50% of sleep minutes must have HR
DAY_HR_MIN_MIN = 600  # >= 10 h of awake worn minutes 06-24 for daytime HR stats
LONG_WAKE_S = 300  # wake segment >= 5 min = 'long awakening'

NIGHT_FEATS = ["deep_min", "rem_min", "light_min", "wake_min", "wake_pct", "deep_pct", "rem_pct", "wake_count", "wake_long_n",
               "wake_per_h", "min_to_fall", "min_after_wake", "awake_in_bed",
               "ss_overall", "ss_composition", "ss_revitalization", "ss_duration", "ss_deep", "ss_restless",
               "hr_sleep_mean", "hr_sleep_p5"]
DAY_FEATS = ["z_fatburn", "z_cardio", "z_peak", "z_cardio_peak", "z_below",
             "ex_user_min", "ex_avg_hr", "ex_cp_min", "hr_day_mean", "hr_day_p10"]


# ---------------------------------------------------------------- sleep levels + sleep score
def sleep_levels(pid: str) -> pd.DataFrame:
    rows = []
    for e in _fb(pid, "sleep.json") or []:
        if not e.get("mainSleep"):
            continue
        lv = e.get("levels", {})
        sm = lv.get("summary", {})
        r = dict(logId=e["logId"], sleep_type=e["type"], minutesAsleep=e["minutesAsleep"],
                 wake_min=e["minutesAwake"],  # stages: = wake.minutes; classic: = awake + restless (harmonised)
                 min_to_fall=e["minutesToFallAsleep"], min_after_wake=e["minutesAfterWakeup"],
                 awake_in_bed=e["timeInBed"] - e["minutesAsleep"])
        if e["type"] == "stages":
            for st in ["deep", "rem", "light"]:
                r[f"{st}_min"] = sm.get(st, {}).get("minutes", np.nan)
            r["wake_count"] = sm.get("wake", {}).get("count", np.nan)
            data = lv.get("data", [])
            # long awakenings: wake segments >= 5 min, not the first/last segment (sleep onset / final wake)
            r["wake_long_n"] = sum(1 for i, s in enumerate(data)
                                   if s["level"] == "wake" and s["seconds"] >= LONG_WAKE_S and 0 < i < len(data) - 1)
            # awake share of time in bed (transparent alternative to Fitbit's proprietary `efficiency`)
            r["wake_pct"] = 100 * e["minutesAwake"] / e["timeInBed"] if e["timeInBed"] else np.nan
            r["stage_check"] = sum(sm.get(k, {}).get("minutes", 0) for k in ["deep", "rem", "light"]) - e[
                "minutesAsleep"]
        else:
            for st in ["deep", "rem", "light"]:
                r[f"{st}_min"] = np.nan
            r["wake_count"] = np.nan  # classic counts (awake+restless) have different semantics
            r["wake_long_n"] = np.nan
            r["wake_pct"] = np.nan  # classic awake+restless is not comparable (median 17 vs 57 min)
            r["classic_restless_min"] = sm.get("restless", {}).get("minutes", np.nan)
            r["classic_awake_min"] = sm.get("awake", {}).get("minutes", np.nan)
        rows.append(r)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates("logId")  # sleep.json contains exact duplicate entries
    df["deep_pct"] = 100 * df.deep_min / df.minutesAsleep
    df["rem_pct"] = 100 * df.rem_min / df.minutesAsleep
    df["wake_per_h"] = df.wake_count / (df.minutesAsleep / 60)
    ss = pd.read_csv(ROOT / pid / "fitbit" / "sleep_score.csv")
    ss = ss.rename(columns={"sleep_log_entry_id": "logId", "overall_score": "ss_overall",
                            "composition_score": "ss_composition", "revitalization_score": "ss_revitalization",
                            "duration_score": "ss_duration", "deep_sleep_in_minutes": "ss_deep",
                            "restlessness": "ss_restless"})
    ss = ss[["logId", "ss_overall", "ss_composition", "ss_revitalization", "ss_duration", "ss_deep",
             "ss_restless"]].drop_duplicates("logId")
    return df.merge(ss, on="logId", how="left")


# ---------------------------------------------------------------- HR zones + exercise (daily)
def hr_zones(pid: str) -> pd.DataFrame:
    z = _fb(pid, "time_in_heart_rate_zones.json") or []
    rows = []
    for x in z:
        v = x["value"]["valuesInZones"]
        rows.append(dict(date=pd.Timestamp(x["dateTime"][:10]), z_below=v.get("BELOW_DEFAULT_ZONE_1"),
                         z_fatburn=v.get("IN_DEFAULT_ZONE_1"), z_cardio=v.get("IN_DEFAULT_ZONE_2"),
                         z_peak=v.get("IN_DEFAULT_ZONE_3"), z_custom=int("IN_CUSTOM_ZONE" in v)))
    df = pd.DataFrame(rows).groupby("date").first()
    df["z_cardio_peak"] = df.z_cardio + df.z_peak
    df["z_total"] = df[["z_below", "z_fatburn", "z_cardio", "z_peak"]].sum(axis=1)
    return df


def exercise_day(pid: str) -> pd.DataFrame:
    ex = _fb(pid, "exercise.json") or []
    rows = []
    for x in ex:
        mins = x.get("activeDuration", x.get("duration", 0)) / 60000
        zones = {z["name"]: z.get("minutes", 0) for z in x.get("heartRateZones", [])}
        rows.append(dict(date=pd.Timestamp(x["startTime"][:10]), name=x["activityName"], mins=mins,
                         user=x.get("logType") in ("tracker", "manual", "mobile_run"),
                         hr=x.get("averageHeartRate", np.nan),
                         cp=zones.get("Cardio", 0) + zones.get("Peak", 0)))
    e = pd.DataFrame(rows)
    if e.empty:
        return pd.DataFrame(columns=["ex_user_min", "ex_avg_hr", "ex_cp_min"])
    nw = e[e.name != "Walk"].copy()
    nw["hrw"] = nw.hr * nw.mins
    g = nw.groupby("date")
    out = pd.DataFrame({
        "ex_user_min": e[e.user].groupby("date").mins.sum(),
        # duration-weighted average HR over non-walk sessions (only days with such a session)
        "ex_avg_hr": g.hrw.sum() / g.mins.sum(),
        "ex_cp_min": e.groupby("date").cp.sum(),
    })
    return out


# ---------------------------------------------------------------- heart_rate.json (heavy)
def hr_minutes(pid: str) -> pd.Series:
    """Per-minute mean bpm (confidence > 0, 30..220 bpm), index = local minute timestamp."""
    raw = (ROOT / pid / "fitbit" / "heart_rate.json").read_bytes()
    m = HR_PAT.findall(raw)
    del raw
    a = np.array(m, dtype=object)
    del m
    date = pd.to_datetime(pd.Series(a[:, 0]).str.decode("ascii"))
    h = a[:, 1].astype(int)
    mi = a[:, 2].astype(int)
    bpm = a[:, 4].astype(int)
    conf = a[:, 5].astype(int)
    del a
    ts = date + pd.to_timedelta(h * 60 + mi, unit="m")
    s = pd.Series(bpm, index=ts.to_numpy())
    ok = (conf > 0) & (bpm >= 30) & (bpm <= 220)
    s = s[ok]
    return s.groupby(level=0).mean().sort_index()


def hr_derived(pid: str, nights: pd.DataFrame, redo=False) -> pd.DataFrame:
    """nights: selected main sleeps (pid rows of sleep_night.csv). Returns long table kind/date/feature."""
    HRDIR.mkdir(exist_ok=True)
    out = HRDIR / f"{pid}.csv"
    if out.exists() and not redo:
        return pd.read_csv(out, parse_dates=["date"])
    s = hr_minutes(pid)
    idx = s.index.values
    vals = s.to_numpy()
    rows = []
    # night: HR minutes inside the selected main sleep
    for _, n in nights.iterrows():
        st, en = np.datetime64(pd.Timestamp(n.start)), np.datetime64(pd.Timestamp(n.end))
        i0, i1 = np.searchsorted(idx, st), np.searchsorted(idx, en)
        v = vals[i0:i1]
        dur = (pd.Timestamp(n.end) - pd.Timestamp(n.start)).total_seconds() / 60
        cover = len(v) / dur if dur > 0 else 0
        rows.append(dict(kind="night", date=n.date, logId=n.logId, hr_cover=cover, hr_n=len(v),
                         hr_sleep_mean=v.mean() if len(v) else np.nan,
                         hr_sleep_p5=np.percentile(v, 5) if len(v) else np.nan))
    # day: worn minutes of the calendar day outside any sleep record (main or nap)
    asleep = np.zeros(len(idx), bool)
    for e in _fb(pid, "sleep.json") or []:
        st = np.datetime64(pd.Timestamp(e["startTime"].replace("T", " ")))
        en = np.datetime64(pd.Timestamp(e["endTime"].replace("T", " ")))
        asleep[np.searchsorted(idx, st):np.searchsorted(idx, en)] = True
    t = pd.DatetimeIndex(idx)
    day = t.normalize()
    keep = ~asleep  # whole calendar day, awake (night owls like P16 are awake 14-06)
    dd = pd.DataFrame({"date": day[keep], "v": vals[keep]})
    g = dd.groupby("date").v
    agg = pd.DataFrame({"hr_day_n": g.size(), "hr_day_mean": g.mean(), "hr_day_p10": g.quantile(0.10)})
    agg = agg.reset_index()
    agg["kind"] = "day"
    res = pd.concat([pd.DataFrame(rows), agg], ignore_index=True)
    res.insert(0, "pid", pid)
    res.to_csv(out, index=False)
    del s, idx, vals, asleep, t, dd
    return res


# ---------------------------------------------------------------- assemble
def main(redo_hr=False):
    sn = pd.read_csv(CACHE / "sleep_night.csv", parse_dates=["date", "start", "end"])
    fd = pd.read_csv(CACHE / "fitbit_day.csv", parse_dates=["date"])
    daily = pd.read_csv(CACHE / "daily.csv", parse_dates=["date", "ts_local"])
    nights_all, days_all, feats = [], [], []
    for pid in PIDS:
        sel = sn[sn.pid == pid]
        lv = sleep_levels(pid)
        night = sel[["pid", "date", "logId", "start", "end", "sleep_h"]].merge(lv, on="logId", how="left") \
            if len(sel) and len(lv) else sel[["pid", "date", "logId"]].copy()
        try:
            hr = hr_derived(pid, sel, redo=redo_hr) if len(sel) or True else None
            print(pid, "hr ok", len(hr), flush=True)
        except FileNotFoundError:
            hr = None
        if hr is not None and len(hr):
            hn = hr[hr.kind == "night"][["logId", "hr_cover", "hr_sleep_mean", "hr_sleep_p5"]]
            night = night.merge(hn, on="logId", how="left") if len(night) else night
            if "hr_cover" in night:
                bad = night.hr_cover < NIGHT_HR_MIN_COVER
                night.loc[bad, ["hr_sleep_mean", "hr_sleep_p5"]] = np.nan
            hd = hr[hr.kind == "day"][["date", "hr_day_n", "hr_day_mean", "hr_day_p10"]].set_index("date")
        else:
            hd = pd.DataFrame(columns=["hr_day_n", "hr_day_mean", "hr_day_p10"])
        for c in NIGHT_FEATS:
            if c not in night:
                night[c] = np.nan
        nights_all.append(night)

        f = fd[fd.pid == pid].set_index("date")[["wear_min", "wear_day"]]
        day = f.join(hr_zones(pid), how="outer").join(exercise_day(pid), how="outer").join(hd, how="outer")
        # exercise on a worn day without any logged exercise = 0 (Fitbit auto-detects, so absence is informative)
        for c in ["ex_user_min", "ex_cp_min"]:
            day[c] = day[c].fillna(0)
        day.loc[day.hr_day_n < DAY_HR_MIN_MIN, ["hr_day_mean", "hr_day_p10"]] = np.nan
        day["pid"] = pid
        days_all.append(day.reset_index())

        # ---- align on survey day D (same rules as build_daily)
        dv = daily[daily.pid == pid].reset_index(drop=True)
        D = dv.date
        out = dv[["pid", "date", "ts_local", "sleep_after_survey"]].copy()
        ni = night.set_index("date") if len(night) else pd.DataFrame(columns=NIGHT_FEATS)
        out["sleep_type_lag1"] = ni["sleep_type"].reindex(D).to_numpy() if "sleep_type" in ni else np.nan
        for c in NIGHT_FEATS:
            s = pd.to_numeric(ni[c], errors="coerce") if c in ni else pd.Series(dtype=float)
            out[f"{c}_lag1"] = _lagged(s, D, [0], 1)
            out[f"{c}_avg3"] = _lagged(s, D, [0, 1, 2], 2)
            m = out.sleep_after_survey.to_numpy(bool)
            out.loc[m, f"{c}_lag1"] = np.nan
            out.loc[m, f"{c}_avg3"] = _lagged(s, D, [1, 2], 2)[m]
        valid = day.wear_day >= DEFAULT_WEAR_DAY_MIN
        for c in DAY_FEATS:
            s = day[c].where(valid)
            out[f"{c}_lag1"] = _lagged(s, D, [1], 1)
            out[f"{c}_avg3"] = _lagged(s, D, [1, 2, 3], 2)
        feats.append(out)

    N = pd.concat(nights_all, ignore_index=True)
    Dy = pd.concat(days_all, ignore_index=True)
    F = pd.concat(feats, ignore_index=True)
    N.to_csv(CACHE / "extra_night.csv", index=False)
    Dy.to_csv(CACHE / "extra_day.csv", index=False)
    F.to_csv(CACHE / "extra_features.csv", index=False)
    print("wrote extra_night", len(N), "extra_day", len(Dy), "extra_features", len(F))


if __name__ == "__main__":
    main(redo_hr="--redo-hr" in sys.argv)
