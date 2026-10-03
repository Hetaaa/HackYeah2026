"""Per-day content for the calendar and day view.

reasons  "Possible reason" only from SIGNIFICANT patterns whose condition holds that day
         (bad days: bad patterns, good days: good patterns), max 2; otherwise NO_REASON.
         No |z| fallback: validation showed it fires on 34 % of neutral days (= noise).
compare  every day, descriptive: up to 2 search features (lag1) that differ from the person's
         average good day by >= 1 SD of good days. People with < 10 good days are compared
         with their average day.
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
                "pattern_text": p["text"],
                "text": texts.reason_text(p["feature"], p["variant"], x),
                "_score": p["score"],
            }
        )
    found.sort(key=lambda r: (-r["_score"], -abs(r["z"] or 0)))
    return [{k: v for k, v in r.items() if k != "_score"} for r in found[: C.MAX_REASONS]]


def compare_day(row: pd.Series, nrm: dict, feats: list[str], ref: str) -> list[dict]:
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
                    "text": texts.compare_text(name, d, ref),
                    "_abs_z": abs(z),
                }
            )
    out.sort(key=lambda r: (-r["_abs_z"], r["feature"]))  # unrounded |z|, ties by name
    return [{k: v for k, v in r.items() if k != "_abs_z"} for r in out[: C.COMPARE_MAX]]


def values(row: pd.Series, nrm: dict) -> list[dict]:
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
            }
        )
    return out
