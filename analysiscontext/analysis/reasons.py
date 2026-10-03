"""Feature 2: calendar with possible reasons + English texts for patterns (koncepcja-analityczna.md sec. 3).

For every day of an included participant (incl. post-lockdown days, patterns frozen on the analysis window):
  norm      median / MAD of each feature column on the person's good days in the analysis window
            (fewer than 10 good days -> all window days), robust z = (x - median) / max(1.4826 MAD, floor)
  bad day   significant bad patterns whose condition holds that day, sorted by pattern score, then |z|; max 2;
            none -> "nothing stands out" (no |z| fallback: validation showed it fires on 34% of neutral days)
  good day  symmetric with good patterns
  neutral   no reasons
  compare   every day (descriptive, not causal): up to 2 search features (lag1) differing from the person's
            average good day by >= 1 SD of good days ("You slept 1 h less than on your average good day");
            people with < 10 good days are compared with their average day instead

Usage: uv run --with pandas --with numpy python reasons.py   -> output/patterns.json, output/calendar.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from HackYeah2026.analysiscontext.analysis.engine import OUT, Settings, analysis_rows, load, run_all, search_features

MIN_NORM_DAYS = 10
COMPARE_MIN_Z = 1.0  # descriptive block: only differences of >= 1 SD of the person's good days
COMPARE_MAX = 2
Z_FLOOR = {"sleep_h": 0.25, "bedtime_h": 0.25, "wake_pct": 1.0, "rem_pct": 1.0, "hr_sleep_mean": 1.0,
           "steps": 500, "mvpa": 5, "z_cardio_peak": 5, "lightly": 10, "sleep_eff": 1.0, "rhr_night": 1.0,
           "time_in_bed_h": 0.25, "sedentary": 15, "wake_min": 3, "deep_pct": 1.0, "ss_overall": 2}
NIGHT = {"sleep_h", "bedtime_h", "wake_pct", "rem_pct", "hr_sleep_mean", "sleep_eff", "rhr_night",
         "time_in_bed_h", "wake_min", "deep_pct", "ss_overall"}


# ---------------------------------------------------------------- formatting
def hours(v: float) -> str:
    h, m = divmod(int(round(v * 60)), 60)
    if h == 0:
        return f"{m} min"
    return f"{h} h" if m == 0 else f"{h} h {m:02d} min"


def clock(v: float) -> str:
    """bedtime_h = hours since 18:00 of the previous evening."""
    t = int(round((18 + v) * 60)) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def fmt(feature: str, v: float) -> str:
    if feature in ("sleep_h", "time_in_bed_h"):
        return hours(v)
    if feature == "bedtime_h":
        return clock(v)
    if feature in ("wake_pct", "rem_pct", "deep_pct"):
        return f"{v:.0f}%" if float(v).is_integer() else f"{v:.1f}%"  # 12.4% must not print as threshold 12%
    if feature in ("hr_sleep_mean", "rhr_night"):
        return f"{v:.0f} bpm"
    if feature == "steps":
        return f"{v:,.0f}"
    return f"{v:.0f} min"


CONDITION = {  # (bad side / below phrase, above phrase) with {v}
    "sleep_h": ("you sleep under {v}", "you sleep over {v}"),
    "bedtime_h": ("you fall asleep before {v}", "you fall asleep after {v}"),
    "wake_pct": ("you are awake under {v} of the night", "you are awake over {v} of the night"),
    "rem_pct": ("your REM sleep is under {v}", "your REM sleep is over {v}"),
    "hr_sleep_mean": ("your heart rate during sleep is under {v}", "your heart rate during sleep is over {v}"),
    "steps": ("you walk fewer than {v} steps", "you walk more than {v} steps"),
    "mvpa": ("you get under {v} of brisk activity", "you get over {v} of brisk activity"),
    "z_cardio_peak": ("you spend under {v} in high heart-rate zones",
                      "you spend over {v} in high heart-rate zones"),
    "lightly": ("you get under {v} of light activity", "you get over {v} of light activity"),
    "sleep_eff": ("your sleep efficiency is under {v}", "your sleep efficiency is over {v}"),
}
VALUE = {  # night features: phrase for last night; avg3 replaces "last night" with the 3-night window
    "sleep_h": "you slept {v} last night", "bedtime_h": "you fell asleep at {v} last night",
    "wake_pct": "you were awake {v} of last night", "rem_pct": "your REM sleep was {v} last night",
    "hr_sleep_mean": "your heart rate during sleep was {v} last night",
    "steps": "you walked {v} steps", "mvpa": "you had {v} of brisk activity",
    "z_cardio_peak": "you spent {v} in high heart-rate zones", "lightly": "you had {v} of light activity",
    "sleep_eff": "your sleep efficiency was {v} last night",
}


def window(feature: str, variant: str) -> str:
    """Time window phrase; empty for last night (night phrases already say it)."""
    night = feature in NIGHT
    if variant == "avg3":
        return " on average over the last 3 nights" if night else " on average over the previous 3 days"
    return "" if night else " the day before"


def value_text(feature: str, variant: str, x: float) -> str:
    t = VALUE[feature].format(v=fmt(feature, x))
    if variant == "avg3":
        t = t.replace(" last night", "")
    return t + window(feature, variant)


def pattern_text(p: dict) -> str:
    f, v = p["feature"], fmt(p["feature"], p["threshold"])
    cond = CONDITION[f][p["op"] == "above"].format(v=v)
    w = window(f, p["variant"])
    lead = "" if p["level"] == "significant" else "Early signal: "
    return (f"{lead}When {cond}{w}, {p['target_days_in_condition']} of {p['days_in_condition']} days were "
            f"{p['kind']} days (vs {p['rate_out']:.0%} otherwise).")


# ---------------------------------------------------------------- norms + reasons
def norms(rows: pd.DataFrame, cols: list[str]) -> tuple[dict, str]:
    good = rows[rows.label == "good"]
    base, src = (good, "good_days") if len(good) >= MIN_NORM_DAYS else (rows, "all_days")
    out = {}
    for c in cols:
        x = base[c].dropna()
        if len(x) < 3:
            continue
        med = float(x.median())
        mad = float((x - med).abs().median()) * 1.4826
        floor = Z_FLOOR[c.rsplit("_", 1)[0]]
        # degenerate = no spread on norm days (e.g. 0 min in HR zones on every good day): z is meaningless
        out[c] = {"median": med, "scale": max(mad, floor), "degenerate": mad == 0,
                  "mean": float(x.mean()), "sd": max(float(x.std(ddof=0)), floor)}
    return out, src


def holds(p: dict, x: float) -> bool:
    if np.isnan(x):
        return False
    return x < p["threshold"] if p["op"] == "below" else x > p["threshold"]


def day_reasons(row: pd.Series, pats: list[dict], nrm: dict) -> list[dict]:
    out = []
    for p in pats:  # significant patterns active today
        x = row[p["column"]]
        if p["level"] != "significant" or not holds(p, x):
            continue
        n = nrm.get(p["column"])
        z = (x - n["median"]) / n["scale"] if n else np.nan
        out.append(dict(source="pattern", feature=p["feature"], column=p["column"], value=float(x),
                        norm=n["median"] if n else None, z=round(float(z), 2), _score=p["score"],
                        text=f"Possible reason: {value_text(p['feature'], p['variant'], x)}."))
    if out:
        out.sort(key=lambda r: (-r["_score"], -abs(r["z"]) if np.isfinite(r["z"]) else 0))
        return [{k: v for k, v in r.items() if k != "_score"} for r in out[:2]]
    return [dict(source="none", text="Nothing in your watch data stands out — the reason may be outside "
                                     "what we measure.")]


def diff_text(f: str, d: float, ref: str) -> str:
    """Sentence comparing a day's value with the reference (average good day)."""
    more = d > 0
    a = abs(d)
    if f == "sleep_h":
        return f"You slept {hours(a)} {'more' if more else 'less'} than {ref}."
    if f == "bedtime_h":
        return f"You fell asleep {hours(a)} {'later' if more else 'earlier'} than {ref}."
    if f == "wake_pct":
        return f"You were awake {a:.0f} percentage points {'more' if more else 'less'} of the night than {ref}."
    if f == "rem_pct":
        return f"Your REM sleep was {a:.0f} percentage points {'higher' if more else 'lower'} than {ref}."
    if f == "hr_sleep_mean":
        return f"Your heart rate during sleep was {a:.0f} bpm {'higher' if more else 'lower'} than {ref}."
    if f == "steps":
        return f"The day before you walked {a:,.0f} {'more' if more else 'fewer'} steps than {ref}."
    what = {"mvpa": "brisk activity", "z_cardio_peak": "time in high heart-rate zones",
            "lightly": "light activity"}[f]
    return f"The day before you had {a:.0f} min {'more' if more else 'less'} {what} than {ref}."


def compare_day(row: pd.Series, nrm: dict, feats: list[str], ref: str) -> list[dict]:
    """Descriptive, not causal: up to 2 search features (lag1) furthest from the average good day (|z| >= 1)."""
    out = []
    for f in feats:
        col = f"{f}_lag1"
        x, n = row.get(col, np.nan), nrm.get(col)
        if n is None or n["degenerate"] or pd.isna(x):
            continue
        d = float(x) - n["mean"]
        z = d / n["sd"]
        if abs(z) >= COMPARE_MIN_Z:
            out.append(dict(feature=f, column=col, value=round(float(x), 3), reference=round(n["mean"], 3),
                            diff=round(d, 3), z=round(z, 2), text=diff_text(f, d, ref)))
    out.sort(key=lambda r: -abs(r["z"]))
    return out[:COMPARE_MAX]


def build():
    daily, participants, config = load()
    patterns = run_all(daily, participants, config)
    for r in patterns.values():
        for kind in ("bad", "good"):
            for p in r[kind]["patterns"]:
                p["text"] = pattern_text(p)
    view_cols = [c for f, spec in config["features"].items() for c in spec["columns"]]
    calendar = {}
    for pid, info in participants.items():
        if not info["included"]:
            continue
        win = analysis_rows(daily, pid)
        nrm, src = norms(win, [c for c in view_cols if c in daily])
        feats = list(search_features(config, info["group_E_feature"], Settings()))
        ref = "on your average good day" if src == "good_days" else "on your average day"
        days = daily[daily.pid == pid].sort_values("date")
        out = []
        for _, row in days.iterrows():
            label = row.label if isinstance(row.label, str) else None
            reasons = []
            if label in ("bad", "good"):
                reasons = day_reasons(row, patterns[pid][label]["patterns"], nrm)
            values = {c: (None if pd.isna(row[c]) else round(float(row[c]), 3)) for c in view_cols if c in row}
            out.append(dict(date=str(row.date.date()), label=label,
                            z=None if pd.isna(row.z) else round(float(row.z), 3),
                            post_lockdown=bool(row.post_lockdown), reasons=reasons,
                            compare=compare_day(row, nrm, feats, ref), values=values))
        calendar[pid] = {"norm_source": src,
                         "norms": {c: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in n.items()}
                                   for c, n in nrm.items()},
                         "days": out}
    (OUT / "patterns.json").write_text(json.dumps(patterns, indent=2, sort_keys=True))
    (OUT / "calendar.json").write_text(json.dumps(calendar, indent=2, sort_keys=True))
    return patterns, calendar


if __name__ == "__main__":
    patterns, calendar = build()
    for pid, r in patterns.items():
        for kind in ("bad", "good"):
            for p in r[kind]["patterns"]:
                print(pid, p["text"])
    for pid, c in calendar.items():
        src = pd.Series([r["source"] for d in c["days"] for r in d["reasons"]]).value_counts().to_dict()
        print(pid, "reasons:", src)
