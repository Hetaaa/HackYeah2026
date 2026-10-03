"""Final cleaning of PMData -> analysis/output/ (frozen spec: analiza-pmdata.md sec. 12 + runda2 sec. 8-9).

Outputs (analysis/output/):
  daily_clean.csv      kept participants (gates passed), one row per pid x survey day D
  daily_personas.csv   same schema, personas only (+ persona_role)
  participants.json    all 16 participants: gates, label parameters, group E feature, N per step
  feature_config.json  feature catalogue (group, direction, grid step, search/view) + engine parameters
  cleaning_log.csv     N per participant after each cleaning step

Frozen decisions:
  label     mood + fatigue + stress, centred on the person's median, median/SD fitted on pre-lockdown days,
            dead zone |z| <= 0.5 -> neutral
  features  watch only; group E = z_cardio_peak (HR zones) when the person has >= 20 days with > 10 min,
            otherwise mvpa
  personas  P06, P01, P10 (main), P16 (backup)

Reuses loaders from build_daily.py / build_extra.py. Heavy inputs come from cache/wear_minutes.csv and
cache/hr_derived/ (use --rebuild-cache to recompute them from heart_rate.json).

Usage: uv run --with pandas --with numpy --with pyarrow python clean.py [--rebuild-cache]
"""
from __future__ import annotations

import argparse
import json
import warnings

import numpy as np
import pandas as pd

import HackYeah2026.analysiscontext.analysis.build_wear as build_wear
from HackYeah2026.analysiscontext.analysis.build_daily import (CACHE, DEFAULT_WEAR_DAY_MIN, PIDS, SED_WEAR_MIN, SLEEP_END_TOL_MIN, _lagged,
                         load_fitbit_day, load_sleep, load_survey)
from HackYeah2026.analysiscontext.analysis.build_extra import NIGHT_HR_MIN_COVER, hr_derived, hr_zones, sleep_levels

warnings.filterwarnings("ignore")
OUT = CACHE.parent / "output"

LOCKDOWN = pd.Timestamp("2020-03-12")
HOLIDAY = (pd.Timestamp("2019-12-21"), pd.Timestamp("2020-01-01"))
LABEL_FIELDS = ["mood", "fatigue", "stress"]
SURVEY_RAW = ["mood", "fatigue", "stress", "readiness", "soreness", "sleep_quality", "sleep_duration_h"]
DEAD_ZONE = 0.5

# gates
MIN_RAW_SD = 0.20
MIN_FULL_DAYS = 60
MIN_BAD_DAYS = 15
MIN_GOOD_DAYS = 15
E_HRZ_MIN_DAYS = 20  # days with z_cardio_peak > E_HRZ_MIN_MIN in the analysis window
E_HRZ_MIN_MIN = 10

PERSONAS = {"p06": "main", "p01": "main", "p10": "main", "p16": "backup"}

# feature catalogue: column -> (group, variants, bad-day direction, grid step, mode)
FEATURES = {
    "sleep_h": ("A", ["lag1", "avg3"], "below", 0.5, "search"),
    "bedtime_h": ("B", ["lag1", "avg3"], "above", 0.5, "search"),
    "wake_pct": ("C", ["lag1"], "above", 1.0, "search"),
    "steps": ("D", ["lag1", "avg3"], "below", 1000, "search"),
    "z_cardio_peak": ("E", ["lag1", "avg3"], "above", 10, "search"),
    "mvpa": ("E", ["lag1", "avg3"], "below", 10, "search"),
    "lightly": ("F", ["lag1", "avg3"], "below", 20, "search"),
    "rem_pct": ("G", ["lag1"], "below", 2.0, "search"),
    "hr_sleep_mean": ("I", ["lag1"], "above", 1.0, "search"),
    "sleep_eff": ("C", ["lag1"], "below", 1.0, "view"),
    "rhr_night": ("I", ["lag1"], "above", 1.0, "view"),
    "time_in_bed_h": ("A", ["lag1"], "below", 0.5, "view"),
    "sedentary": ("D", ["lag1"], "above", 30, "view"),
    "wake_min": ("C", ["lag1"], "above", 5, "view"),
    "deep_pct": ("G", ["lag1"], "below", 2.0, "view"),
    "ss_overall": ("A", ["lag1"], "below", 5, "view"),
}
NIGHT_COLS = ["sleep_h", "bedtime_h", "wake_pct", "rem_pct", "hr_sleep_mean", "sleep_eff", "rhr_night",
              "time_in_bed_h", "wake_min", "deep_pct", "ss_overall"]
DAY_COLS = ["steps", "z_cardio_peak", "mvpa", "lightly", "sedentary"]
# hard validity ranges (value outside -> NaN)
VALID = {
    "sleep_h": (2, 14), "wake_pct": (0, 50), "rem_pct": (0, 50), "hr_sleep_mean": (35, 110),
    "rhr_night": (30, 110), "steps": (0, 60000),
}
ENGINE = {"min_support": 10, "max_cover": 0.5, "fallback": None,
          "max_reasons_per_day": 2, "max_patterns_per_kind": 3, "dead_zone": DEAD_ZONE,
          "analysis_window_end": str(LOCKDOWN.date()), "permutation": "circular_shift_all_offsets_min14",
          "significance": "95th_percentile_of_max_statistic"}


# ---------------------------------------------------------------- per-participant pieces
def _variants(c: str) -> list[str]:
    return FEATURES[c][1]


def nights_for(pid: str) -> pd.DataFrame:
    """Selected main sleep per wake date with all night features (validated)."""
    sl = load_sleep(pid)
    if sl.empty:
        return pd.DataFrame(columns=["date", "logId", "end", "sleep_type"] + NIGHT_COLS)
    lv = sleep_levels(pid)
    keep = ["logId", "sleep_type", "wake_pct", "rem_pct", "deep_pct", "wake_min", "ss_overall"]
    n = sl.merge(lv[keep], on="logId", how="left") if len(lv) else sl.assign(
        **{c: np.nan for c in keep[1:]})
    try:
        hr = hr_derived(pid, sl)
        hn = hr[hr.kind == "night"][["logId", "hr_cover", "hr_sleep_mean"]].drop_duplicates("logId")
        n = n.merge(hn, on="logId", how="left")
        n.loc[n.hr_cover < NIGHT_HR_MIN_COVER, "hr_sleep_mean"] = np.nan
    except FileNotFoundError:
        n["hr_sleep_mean"] = np.nan
    stages = n.sleep_type == "stages"
    for c in ["wake_pct", "rem_pct", "deep_pct"]:
        n.loc[~stages, c] = np.nan
    for c, (lo, hi) in VALID.items():
        if c in n:
            n[c] = n[c].where(n[c].between(lo, hi))
    n["date"] = pd.to_datetime(n.date)
    n["end"] = pd.to_datetime(n.end)
    return n[["date", "logId", "end", "sleep_type"] + NIGHT_COLS]


def days_for(pid: str, wear: pd.DataFrame) -> pd.DataFrame:
    """Calendar-day activity features, NaN on non-wear days."""
    fd = load_fitbit_day(pid, wear).set_index("date")
    try:
        fd = fd.join(hr_zones(pid)[["z_cardio_peak"]], how="left")
    except (KeyError, TypeError):
        fd["z_cardio_peak"] = np.nan
    nonwear = fd.wear_day < DEFAULT_WEAR_DAY_MIN
    fd.loc[nonwear, DAY_COLS] = np.nan
    fd.loc[fd.wear_min < SED_WEAR_MIN, "sedentary"] = np.nan
    fd["steps"] = fd.steps.where(fd.steps.between(*VALID["steps"]))
    return fd


def align(pid: str, wear: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    sv = load_survey(pid)
    first = sv[sv.rank_in_day == 0].reset_index(drop=True)
    D = first.date
    nights = nights_for(pid).set_index("date")
    days = days_for(pid, wear)

    out = first[["pid", "date", "ts_local", "night_report"] + SURVEY_RAW].copy()
    out["weekday"] = D.dt.dayofweek
    end_D = nights.end.reindex(D).reset_index(drop=True)
    out["sleep_after_survey"] = (end_D > out.ts_local + pd.Timedelta(minutes=SLEEP_END_TOL_MIN)).to_numpy()
    out["sleep_type"] = nights.sleep_type.reindex(D).to_numpy()
    m = out.sleep_after_survey.to_numpy(bool)
    for c in NIGHT_COLS:
        s = pd.to_numeric(nights[c], errors="coerce")
        out[f"{c}_lag1"] = _lagged(s, D, [0], 1)
        out.loc[m, f"{c}_lag1"] = np.nan
        if "avg3" in _variants(c):
            a = _lagged(s, D, [0, 1, 2], 2)
            a[m] = _lagged(s, D, [1, 2], 2)[m]
            out[f"{c}_avg3"] = a
    for c in DAY_COLS:
        out[f"{c}_lag1"] = _lagged(days[c], D, [1], 1)
        if "avg3" in _variants(c):
            out[f"{c}_avg3"] = _lagged(days[c], D, [1, 2, 3], 2)
    wear_dm1 = days.wear_day.reindex(D - pd.Timedelta(days=1)).fillna(0).to_numpy()
    out["nonwear_dm1"] = wear_dm1 < DEFAULT_WEAR_DAY_MIN

    out["post_lockdown"] = D >= LOCKDOWN
    out["weekend_Dm1"] = (D - pd.Timedelta(days=1)).dt.dayofweek >= 5
    out["holiday"] = D.between(*HOLIDAY)
    n_classic = int((nights.sleep_type == "classic").sum())
    log = {"n_reports": len(sv), "n_days": len(first)}
    return out, {"log": log, "classic_nights": n_classic}


# ---------------------------------------------------------------- label
def add_label(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Median-centred composite; median/SD fitted on pre-lockdown days, applied to all days."""
    ok = df[LABEL_FIELDS].notna().all(axis=1)
    fit = ok & ~df.post_lockdown
    params = {}
    dev = pd.DataFrame(index=df.index)
    for f in LABEL_FIELDS:
        med = float(df.loc[fit, f].median()) if fit.any() else np.nan
        sd = float(df.loc[fit, f].std(ddof=0)) if fit.any() else np.nan
        dev[f] = (df[f] - med) / sd if sd and sd > 0 else df[f] * 0.0
        params[f] = {"median": med, "sd": sd}
    comp = dev.mean(axis=1).where(ok)
    sdc = float(comp[fit].std(ddof=0)) if fit.any() else np.nan
    z = comp / sdc if sdc and sdc > 0 else comp * np.nan
    df["comp"] = comp
    df["z"] = z
    df["label"] = pd.Series(np.select([z < -DEAD_ZONE, z > DEAD_ZONE], ["bad", "good"], "neutral"),
                            index=df.index).where(z.notna())
    params["comp_sd"] = sdc
    params["raw_sd"] = float(df.loc[ok, LABEL_FIELDS].mean(axis=1).std(ddof=0)) if ok.any() else np.nan
    return df, params


# ---------------------------------------------------------------- main
def build(rebuild_cache: bool = False) -> dict:
    wear_path = CACHE / "wear_minutes.csv"
    if rebuild_cache or not wear_path.exists():
        wear = pd.concat([build_wear.wear_for(p) for p in PIDS]).sort_values(["pid", "date"])
        wear.to_csv(wear_path, index=False)
    if rebuild_cache:
        for f in (CACHE / "hr_derived").glob("p*.csv"):
            f.unlink()
    wear = pd.read_csv(wear_path)

    frames, participants, logs = [], {}, []
    for pid in PIDS:
        df, meta = align(pid, wear)
        df, lab = add_label(df)
        label_ok = df.label.notna()
        full = label_ok & df.sleep_h_lag1.notna() & df.steps_lag1.notna()
        df["in_analysis_window"] = full & ~df.post_lockdown
        win = df[df.in_analysis_window]
        n_bad, n_good = int((win.label == "bad").sum()), int((win.label == "good").sum())

        reasons = []
        if not (lab["raw_sd"] >= MIN_RAW_SD):
            reasons.append(f"raw_sd {lab['raw_sd']:.3f} < {MIN_RAW_SD}")
        if full.sum() < MIN_FULL_DAYS:
            reasons.append(f"full_days {int(full.sum())} < {MIN_FULL_DAYS}")
        hrz_days = int((win.z_cardio_peak_lag1 > E_HRZ_MIN_MIN).sum())
        log = meta["log"] | {
            "n_label_ok": int(label_ok.sum()),
            "n_sleep_lag1": int(df.sleep_h_lag1.notna().sum()),
            "n_wear_dm1": int((~df.nonwear_dm1).sum()),
            "n_full": int(full.sum()),
            "n_full_prelockdown": int(df.in_analysis_window.sum()),
        }
        participants[pid] = {
            "included": not reasons,
            "exclusion_reasons": reasons,
            "persona_role": PERSONAS.get(pid),
            "label": lab,
            "n_bad_window": n_bad,
            "n_good_window": n_good,
            "bad_patterns_enabled": n_bad >= MIN_BAD_DAYS,
            "good_patterns_enabled": n_good >= MIN_GOOD_DAYS,
            "group_E_feature": "z_cardio_peak" if hrz_days >= E_HRZ_MIN_DAYS else "mvpa",
            "group_E_hrz_days": hrz_days,
            "classic_nights": meta["classic_nights"],
            "n": log,
        }
        logs.append({"pid": pid} | log)
        frames.append(df)

    all_days = pd.concat(frames, ignore_index=True)
    kept = [p for p, v in participants.items() if v["included"]]
    clean = all_days[all_days.pid.isin(kept)].sort_values(["pid", "date"]).reset_index(drop=True)
    personas = clean[clean.pid.isin(PERSONAS)].copy()
    personas["persona_role"] = personas.pid.map(PERSONAS)

    feature_config = {
        "features": {c: {"group": g, "variants": v, "bad_when": d, "grid_step": s, "mode": mode,
                         "columns": [f"{c}_{x}" for x in v]}
                     for c, (g, v, d, s, mode) in FEATURES.items()},
        "groups": {"A": "sleep length", "B": "bedtime", "C": "sleep continuity", "D": "movement volume",
                   "E": "intense effort (z_cardio_peak or mvpa per participant)", "F": "light activity",
                   "G": "sleep structure", "I": "nightly heart rate"},
        "label": {"fields": LABEL_FIELDS, "centre": "median", "fit_window": f"D < {LOCKDOWN.date()}",
                  "dead_zone": DEAD_ZONE},
        "gates": {"min_raw_sd": MIN_RAW_SD, "min_full_days": MIN_FULL_DAYS, "min_bad_days": MIN_BAD_DAYS,
                  "min_good_days": MIN_GOOD_DAYS, "group_E_hrz_min_days": E_HRZ_MIN_DAYS,
                  "group_E_hrz_min_minutes": E_HRZ_MIN_MIN},
        "wear_day_min": DEFAULT_WEAR_DAY_MIN,
        "valid_ranges": VALID,
        "engine": ENGINE,
    }

    for t in (clean, personas):
        t["date"] = t.date.dt.strftime("%Y-%m-%d")
    OUT.mkdir(exist_ok=True)
    fmt = {"index": False, "float_format": "%.6g", "date_format": "%Y-%m-%d %H:%M:%S"}
    clean.to_csv(OUT / "daily_clean.csv", **fmt)
    personas.to_csv(OUT / "daily_personas.csv", **fmt)
    pd.DataFrame(logs).to_csv(OUT / "cleaning_log.csv", index=False)
    (OUT / "participants.json").write_text(json.dumps(participants, indent=2, sort_keys=True, default=float))
    (OUT / "feature_config.json").write_text(json.dumps(feature_config, indent=2, sort_keys=True))
    print(f"kept {len(kept)}: {', '.join(kept)}")
    print("excluded:", {p: v["exclusion_reasons"] for p, v in participants.items() if not v["included"]})
    print(f"daily_clean {len(clean)} rows, personas {len(personas)} rows -> {OUT}")
    return participants


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-cache", action="store_true")
    build(ap.parse_args().rebuild_cache)
