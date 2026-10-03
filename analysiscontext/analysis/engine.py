"""Pattern engine (Feature 1): per-person threshold search + circular-shift max-statistic test.

Spec: koncepcja-analityczna.md sec. 2 + 8a, parameters from output/feature_config.json.

For one person and one kind ("bad" / "good"):
  rows       analysis window (in_analysis_window), ordered by date
  candidates every search feature (one per group; group E per participants.json) x variant x grid threshold
             bad pattern  : feature on the bad side of X   (bad_when below -> x < X, above -> x > X)
             good pattern : feature on the opposite side    (below -> x > X, above -> x < X)
  support    >= min_support valid days inside and outside the condition, condition covers <= max_cover
  score      Wilson lower bound of P(target | cond) - P(target | not cond)
  test       labels circularly shifted by every k in [14, n-14]; null = max score over ALL candidates;
             significant if permutation p = (1 + #null >= score) / (1 + #shifts) <= alpha.
             preliminary = same test against its own feature's null maxima only.

Usage: uv run --with pandas --with numpy python engine.py   -> output/patterns.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "output"
Z95 = 1.959964
MIN_SHIFT = 14


@dataclass
class Settings:
    min_support: int = 10
    max_cover: float = 0.5
    alpha: float = 0.05
    group_c: str = "wake_pct"  # validation can swap in sleep_eff


def load():
    daily = pd.read_csv(OUT / "daily_clean.csv", parse_dates=["date", "ts_local"])
    participants = json.loads((OUT / "participants.json").read_text())
    config = json.loads((OUT / "feature_config.json").read_text())
    return daily, participants, config


def search_features(config: dict, group_e: str, settings: Settings) -> dict[str, dict]:
    feats = {k: v for k, v in config["features"].items() if v["mode"] == "search"}
    drop_e = "mvpa" if group_e == "z_cardio_peak" else "z_cardio_peak"
    feats.pop(drop_e, None)
    if settings.group_c != "wake_pct":
        feats.pop("wake_pct", None)
        feats[settings.group_c] = config["features"][settings.group_c]
    return feats


def grid(x: np.ndarray, step: float, feature: str) -> np.ndarray:
    lo, hi = np.nanpercentile(x, [5, 95])
    if feature == "steps" and hi - lo < 5000:
        step = 500
    if feature == "hr_sleep_mean" and hi - lo > 15:
        step = 2
    g = np.arange(np.ceil(lo / step) * step, np.floor(hi / step) * step + step / 2, step)
    return np.round(g, 6)


def candidates(rows: pd.DataFrame, feats: dict, kind: str):
    """Returns meta list and matrices: IN (cond x n) bool, VALID (cond x n) bool."""
    meta, ins, valids = [], [], []
    for f, spec in feats.items():
        bad_below = spec["bad_when"] == "below"
        below = bad_below if kind == "bad" else not bad_below
        for col in spec["columns"]:
            if col not in rows:
                continue
            x = rows[col].to_numpy(float)
            v = ~np.isnan(x)
            if v.sum() < 2 * 10:
                continue
            for thr in grid(x[v], spec["grid_step"], f):
                cond = (x < thr) if below else (x > thr)
                meta.append(dict(feature=f, group=spec["group"], column=col,
                                 variant=col.rsplit("_", 1)[1], op="below" if below else "above",
                                 threshold=float(thr)))
                ins.append(cond & v)
                valids.append(v)
    if not meta:
        return [], np.zeros((0, len(rows)), bool), np.zeros((0, len(rows)), bool)
    return meta, np.array(ins), np.array(valids)


def wilson_lower(k: np.ndarray, n: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        p = k / n
        z2 = Z95 ** 2
        c = p + z2 / (2 * n) - Z95 * np.sqrt(p * (1 - p) / n + z2 / (4 * n ** 2))
        return c / (1 + z2 / n)


def perm_p(sc: float, null: np.ndarray) -> float:
    return float((1 + (null >= sc).sum()) / (1 + len(null)))


def scores(IN: np.ndarray, VALID: np.ndarray, y: np.ndarray, s: Settings) -> np.ndarray:
    yf = y.astype(float)
    n_in = IN.sum(1)
    n_valid = VALID.sum(1)
    n_out = n_valid - n_in
    k_in = IN @ yf
    k_out = VALID @ yf - k_in
    ok = (n_in >= s.min_support) & (n_out >= s.min_support) & (n_in <= s.max_cover * n_valid)
    with np.errstate(all="ignore"):
        sc = wilson_lower(k_in, n_in) - k_out / n_out
    return np.where(ok, sc, -np.inf)


def run_person(rows: pd.DataFrame, target: np.ndarray, feats: dict, kind: str, s: Settings) -> dict:
    """target: bool array aligned with rows (e.g. label == 'bad'). Returns patterns + test details."""
    meta, IN, VALID = candidates(rows, feats, kind)
    n = len(rows)
    if not meta or n < 2 * MIN_SHIFT + 1:
        return {"patterns": [], "null_q95": None, "n_shifts": 0, "n_candidates": len(meta)}
    obs = scores(IN, VALID, target, s)
    shifts = range(MIN_SHIFT, n - MIN_SHIFT + 1)
    feat_idx = {}
    for i, m in enumerate(meta):
        feat_idx.setdefault(m["feature"], []).append(i)
    null_max, null_feat = [], {f: [] for f in feat_idx}
    for k in shifts:
        sc = scores(IN, VALID, np.roll(target, k), s)
        null_max.append(sc.max())
        for f, idx in feat_idx.items():
            null_feat[f].append(sc[idx].max())
    null_max = np.array(null_max)
    q = np.quantile(null_max, 1 - s.alpha)
    patterns = []
    for f, idx in feat_idx.items():
        i = idx[int(np.argmax(obs[idx]))]
        sc = obs[i]
        if not np.isfinite(sc) or sc <= 0:
            continue
        p_glob = perm_p(sc, null_max)
        p_feat = perm_p(sc, np.array(null_feat[f]))
        if p_glob <= s.alpha:
            level = "significant"
        elif p_feat <= s.alpha:
            level = "preliminary"
        else:
            continue
        cond, v = IN[i], VALID[i]
        n_in, n_out = int(cond.sum()), int(v.sum() - cond.sum())
        k_in = int(target[cond].sum())
        k_out = int(target[v & ~cond].sum())
        patterns.append(meta[i] | dict(
            kind=kind, level=level, score=round(float(sc), 4),
            p_global=round(p_glob, 4), p_feature=round(p_feat, 4),
            days_in_condition=n_in, target_days_in_condition=k_in,
            rate_in=round(k_in / n_in, 4), rate_out=round(k_out / n_out, 4), n_valid=int(v.sum())))
    patterns.sort(key=lambda p: (p["level"] != "significant", -p["score"]))
    return {"patterns": patterns, "null_q95": round(float(q), 4), "n_shifts": len(null_max),
            "n_candidates": len(meta)}


def analysis_rows(daily: pd.DataFrame, pid: str) -> pd.DataFrame:
    return daily[(daily.pid == pid) & daily.in_analysis_window].sort_values("date").reset_index(drop=True)


def run_all(daily, participants, config, s: Settings = Settings(), labels: dict | None = None) -> dict:
    """labels: optional {pid: label array} override (validation)."""
    res = {}
    for pid, info in participants.items():
        if not info["included"]:
            continue
        rows = analysis_rows(daily, pid)
        lab = labels[pid] if labels is not None else rows.label.to_numpy()
        feats = search_features(config, info["group_E_feature"], s)
        out = {}
        for kind, enabled in (("bad", info["bad_patterns_enabled"]), ("good", info["good_patterns_enabled"])):
            if enabled:
                r = run_person(rows, lab == kind, feats, kind, s)
                r["patterns"] = [p for p in r["patterns"] if p["level"] == "preliminary"][:3] \
                    if not any(p["level"] == "significant" for p in r["patterns"]) \
                    else [p for p in r["patterns"] if p["level"] == "significant"][:3]
                out[kind] = r
            else:
                out[kind] = {"patterns": [], "disabled": f"insufficient_{kind}_days"}
        res[pid] = out
    return res


if __name__ == "__main__":
    daily, participants, config = load()
    res = run_all(daily, participants, config)
    (OUT / "patterns.json").write_text(json.dumps(res, indent=2, sort_keys=True))
    for pid, r in res.items():
        for kind in ("bad", "good"):
            for p in r[kind]["patterns"]:
                print(f"{pid} {kind:4} {p['level']:11} {p['column']:20} {p['op']} {p['threshold']:>7g} "
                      f"in {p['target_days_in_condition']}/{p['days_in_condition']} "
                      f"rate {p['rate_in']:.2f} vs {p['rate_out']:.2f} p={p['p_global']}")
