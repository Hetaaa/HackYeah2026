"""Per-day content for the calendar and day view.

reasons  "Possible reason" only from SIGNIFICANT patterns whose condition holds that day
         (bad days: bad patterns, good days: good patterns), max 2; otherwise NO_REASON.
         No |z| fallback: validation showed it fires on 34 % of neutral days (= noise).
compare  every day, descriptive: up to 2 search features (lag1) that differ from the person's
         average good day by >= 1 SD of good days. People with < 10 good days are compared
         with their average day.
leans    whether a value differs from that reference towards the person's own bad days or
         good days (from their good vs bad day means), so the UI can colour it without
         assuming that e.g. more sleep is better.
"""

import numpy as np
import pandas as pd

from app.insights import config as C
from app.insights import texts


def norms(rows: pd.DataFrame) -> tuple[dict, str]:
    """Good-day reference per column: mean/sd (compare) and median/MAD scale (reason z)."""
    good = rows[rows.label == "good"]
    base, source = (good, "good_days") if len(good) >= C.MIN_NORM_DAYS else (rows, "all_days")
    out = {}
    for name, f in C.FEATURES.items():
        for col in f.columns(name):
            x = base[col].dropna() if col in base else pd.Series(dtype=float)
            if len(x) < 3:
                continue
            med = float(x.median())
            mad = float((x - med).abs().median()) * 1.4826
            out[col] = {
                "median": med,
                "scale": max(mad, f.z_floor),
                "degenerate": mad == 0,  # no spread on norm days: z is meaningless
                "mean": float(x.mean()),
                "sd": max(float(x.std(ddof=0)), f.z_floor),
                "p25": float(x.quantile(0.25)),
                "p75": float(x.quantile(0.75)),
            }
    return out, source


def label_stats(rows: pd.DataFrame) -> dict:
    """Per feature (lag1): mean on good and on bad days of the analysis window."""
    out = {}
    for name, f in C.FEATURES.items():
        col = f"{name}_lag1"
        if col not in rows:
            continue
        groups: dict = {}
        for label in ("good", "bad"):
            x = rows.loc[rows.label == label, col].dropna()
            mean = float(x.mean()) if len(x) >= C.STATS_MIN_DAYS else None
            groups[label] = {"n": len(x), "mean": mean}
        both = rows.loc[rows.label.isin(["good", "bad"]), col].dropna()
        groups["sd"] = max(float(both.std(ddof=0)), f.z_floor) if len(both) else f.z_floor
        out[name] = groups
    return out


def drivers(rows: pd.DataFrame, p: dict) -> list[dict]:
    """Label items (mood, fatigue, stress) that move with a pattern: mean answer on days with the
    condition minus days without it. Bad patterns keep items that are worse by >= 0.3 points,
    good patterns items that are better; sorted by size. Descriptive, no significance test."""
    x = rows[p["column"]]
    inside = x.lt(p["threshold"]) if p["op"] == "below" else x.gt(p["threshold"])
    outside = x.notna() & ~inside
    sign = -1 if p["kind"] == "bad" else 1
    found = []
    for item in C.LABEL_FIELDS:
        diff = rows.loc[inside, item].mean() - rows.loc[outside, item].mean()
        if pd.notna(diff) and sign * diff >= C.DRIVER_MIN_DIFF:
            found.append(
                {
                    "item": item,
                    "difference": round(float(diff), 2),
                    "text": texts.driver_text(item, p["kind"]),
                }
            )
    return sorted(found, key=lambda d: -abs(d["difference"]))


def leans(stats: dict, name: str, diff: float) -> str | None:
    """'bad' when a value differs from the reference (`diff` = value - reference) in the
    direction of the person's bad days, 'good' when in the direction of their good days.
    None with too few good or bad days, or when both kinds of days look alike."""
    s = stats.get(name)
    if s is None or diff == 0:
        return None
    good, bad = s["good"], s["bad"]
    if min(good["n"], bad["n"]) < C.LEAN_MIN_DAYS:
        return None
    gap = bad["mean"] - good["mean"]
    if abs(gap) < C.LEAN_MIN_GAP * s["sd"]:
        return None
    return "bad" if (diff > 0) == (gap > 0) else "good"


def _norm_range(n: dict | None) -> dict | None:
    """Median and interquartile range of the reference days (good days)."""
    if n is None:
        return None
    return {"median": round(n["median"], 3), "low": round(n["p25"], 3), "high": round(n["p75"], 3)}


def _holds(p: dict, x: float) -> bool:
    if pd.isna(x):
        return False
    return x < p["threshold"] if p["op"] == "below" else x > p["threshold"]


def day_reasons(row: pd.Series, patterns: list[dict], nrm: dict) -> list[dict]:
    found = []
    for p in patterns:
        x = row[p["column"]]
        if p["level"] != "significant" or not _holds(p, x):
            continue
        n = nrm.get(p["column"])
        z = (x - n["median"]) / n["scale"] if n else np.nan
        found.append(
            {
                "feature": p["feature"],
                "column": p["column"],
                "value": round(float(x), 3),
                "z": round(float(z), 2) if np.isfinite(z) else None,
                "kind": p["kind"],
                "when": p["variant"],
                "pattern_text": p["text"],
                "drivers_text": p["drivers_text"],
                "value_text": texts.value_text(p["feature"], p["variant"], x),
                "text": texts.reason_text(p["feature"], p["variant"], x),
                "_score": p["score"],
            }
        )
    found.sort(key=lambda r: (-r["_score"], -abs(r["z"] or 0)))
    return [{k: v for k, v in r.items() if k != "_score"} for r in found[: C.MAX_REASONS]]


def compare_day(row: pd.Series, nrm: dict, feats: list[str], ref: str, stats: dict) -> list[dict]:
    out = []
    for name in feats:
        col = f"{name}_lag1"
        x, n = row.get(col, np.nan), nrm.get(col)
        if n is None or n["degenerate"] or pd.isna(x):
            continue
        d = float(x) - n["mean"]
        z = d / n["sd"]
        if abs(z) >= C.COMPARE_MIN_Z:
            out.append(
                {
                    "feature": name,
                    "column": col,
                    "value": round(float(x), 3),
                    "reference": round(n["mean"], 3),
                    "norm": _norm_range(n),
                    "diff": round(d, 3),
                    "z": round(z, 2),
                    "leans": leans(stats, name, d),
                    "text": texts.compare_text(name, d, ref),
                    "_abs_z": abs(z),
                }
            )
    out.sort(key=lambda r: (-r["_abs_z"], r["feature"]))  # unrounded |z|, ties by name
    return [{k: v for k, v in r.items() if k != "_abs_z"} for r in out[: C.COMPARE_MAX]]


def values(row: pd.Series, nrm: dict, stats: dict) -> list[dict]:
    """All lag1 features of the day with the person's good-day average, for the day view."""
    out = []
    for name, f in C.FEATURES.items():
        col = f"{name}_lag1"
        x, n = row.get(col, np.nan), nrm.get(col)
        has = not pd.isna(x)
        out.append(
            {
                "feature": name,
                "label": f.label,
                "unit": f.unit,
                "when": "last_night" if f.night else "day_before",
                "mode": f.mode,
                "value": round(float(x), 3) if has else None,
                "display": texts.fmt(name, float(x)) if has else None,
                "reference": round(n["mean"], 3) if n else None,
                "display_reference": texts.fmt(name, n["mean"]) if n else None,
                "norm": _norm_range(n),
                "leans": leans(stats, name, float(x) - n["mean"]) if has and n else None,
            }
        )
    return out
