"""Pattern engine: per-person threshold search + circular-shift max-statistic permutation test.

For one person and one kind ("bad" / "good"):
  rows        analysis window (pre-lockdown, label + sleep + steps present), ordered by date
  candidates  every search feature (group E per person) x variant x "nice" threshold in p5..p95
              bad pattern:  feature on its bad side of X   (bad_when below -> x < X)
              good pattern: feature on the opposite side   (bad_when below -> x > X)
  support     >= MIN_SUPPORT days in and out of the condition, condition covers <= MAX_COVER
  score       Wilson lower bound of P(kind | cond) - P(kind | not cond)
  test        labels shifted circularly by every k in [14, n-14]; null = max score over ALL
              candidates; significant if permutation p <= ALPHA. Preliminary = same test against
              the feature's own null only (shown as "early signal", never used in the calendar).
"""

import numpy as np
import pandas as pd

from app.insights import config as C

Z95 = 1.959964


def search_features(group_e: str) -> dict[str, C.Feature]:
    drop = "mvpa" if group_e == "z_cardio_peak" else "z_cardio_peak"
    return {n: f for n, f in C.FEATURES.items() if f.mode == "search" and n != drop}


def grid(x: np.ndarray, step: float, name: str) -> np.ndarray:
    lo, hi = np.nanpercentile(x, [5, 95])
    if name == "steps" and hi - lo < 5000:
        step = 500
    if name == "hr_sleep_mean" and hi - lo > 15:
        step = 2
    g = np.arange(np.ceil(lo / step) * step, np.floor(hi / step) * step + step / 2, step)
    return np.round(g, 6)


def candidates(rows: pd.DataFrame, feats: dict[str, C.Feature], kind: str):
    meta, ins, valids = [], [], []
    for name, f in feats.items():
        below = (f.bad_when == "below") == (kind == "bad")
        for col in f.columns(name):
            x = rows[col].to_numpy(float)
            v = ~np.isnan(x)
            if v.sum() < 2 * C.MIN_SUPPORT:
                continue
            for thr in grid(x[v], f.grid_step, name):
                cond = (x < thr) if below else (x > thr)
                meta.append(
                    {
                        "feature": name,
                        "group": f.group,
                        "column": col,
                        "variant": col.rsplit("_", 1)[1],
                        "op": "below" if below else "above",
                        "threshold": float(thr),
                    }
                )
                ins.append(cond & v)
                valids.append(v)
    n = len(rows)
    if not meta:
        return [], np.zeros((0, n), bool), np.zeros((0, n), bool)
    return meta, np.array(ins), np.array(valids)


def wilson_lower(k: np.ndarray, n: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        p = k / n
        z2 = Z95**2
        c = p + z2 / (2 * n) - Z95 * np.sqrt(p * (1 - p) / n + z2 / (4 * n**2))
        return c / (1 + z2 / n)


def scores(ins: np.ndarray, valid: np.ndarray, y: np.ndarray) -> np.ndarray:
    yf = y.astype(float)
    n_in = ins.sum(1)
    n_valid = valid.sum(1)
    n_out = n_valid - n_in
    k_in = ins @ yf
    k_out = valid @ yf - k_in
    ok = (n_in >= C.MIN_SUPPORT) & (n_out >= C.MIN_SUPPORT) & (n_in <= C.MAX_COVER * n_valid)
    with np.errstate(all="ignore"):
        sc = wilson_lower(k_in, n_in) - k_out / n_out
    return np.where(ok, sc, -np.inf)


def perm_p(score: float, null: np.ndarray) -> float:
    return float((1 + (null >= score).sum()) / (1 + len(null)))


def run_person(rows: pd.DataFrame, target: np.ndarray, feats: dict, kind: str) -> list[dict]:
    """All patterns passing at least the per-feature test, best per feature, strongest first."""
    meta, ins, valid = candidates(rows, feats, kind)
    n = len(rows)
    if not meta or n < 2 * C.MIN_SHIFT + 1:
        return []
    obs = scores(ins, valid, target)
    by_feature: dict[str, list[int]] = {}
    for i, m in enumerate(meta):
        by_feature.setdefault(m["feature"], []).append(i)
    null_max, null_feat = [], {f: [] for f in by_feature}
    for k in range(C.MIN_SHIFT, n - C.MIN_SHIFT + 1):
        sc = scores(ins, valid, np.roll(target, k))
        null_max.append(sc.max())
        for f, idx in by_feature.items():
            null_feat[f].append(sc[idx].max())
    null_all = np.array(null_max)
    patterns = []
    for f, idx in by_feature.items():
        i = idx[int(np.argmax(obs[idx]))]
        sc = obs[i]
        if not np.isfinite(sc) or sc <= 0:
            continue
        p_global, p_feature = perm_p(sc, null_all), perm_p(sc, np.array(null_feat[f]))
        if p_global <= C.ALPHA:
            level = "significant"
        elif p_feature <= C.ALPHA:
            level = "preliminary"
        else:
            continue
        cond, v = ins[i], valid[i]
        n_in, n_out = int(cond.sum()), int(v.sum() - cond.sum())
        k_in, k_out = int(target[cond].sum()), int(target[v & ~cond].sum())
        patterns.append(
            meta[i]
            | {
                "kind": kind,
                "level": level,
                "score": round(float(sc), 4),
                "p_global": round(p_global, 4),
                "p_feature": round(p_feature, 4),
                "days_in_condition": n_in,
                "target_days_in_condition": k_in,
                "rate_in": round(k_in / n_in, 4),
                "rate_out": round(k_out / n_out, 4),
                "n_valid": int(v.sum()),
            }
        )
    patterns.sort(key=lambda p: (p["level"] != "significant", -p["score"]))
    return patterns


def find_patterns(table: pd.DataFrame, info: dict) -> dict:
    """One user's table -> {"bad": {...}, "good": {...}} with status and up to 3 patterns each."""
    rows = table[table.in_analysis_window].sort_values("date").reset_index(drop=True)
    feats = search_features(info["group_e_feature"])
    out = {}
    for kind in ("bad", "good"):
        if not info["included"]:  # insufficient_days (new user, still collecting) / _variation
            out[kind] = {"status": info["exclusion_reasons"][0], "patterns": []}
            continue
        if not info[f"{kind}_patterns_enabled"]:
            out[kind] = {"status": f"insufficient_{kind}_days", "patterns": []}
            continue
        target = (rows.label == kind).to_numpy()
        found = [_with_shares(p, rows) for p in run_person(rows, target, feats, kind)]
        sig = [p for p in found if p["level"] == "significant"]
        if sig:
            out[kind] = {"status": "ok", "patterns": sig[: C.MAX_PATTERNS]}
        elif found:
            out[kind] = {"status": "preliminary", "patterns": found[: C.MAX_PATTERNS]}
        else:
            out[kind] = {"status": "not_enough_evidence", "patterns": []}
    return out


def _with_shares(p: dict, rows: pd.DataFrame) -> dict:
    """Share of bad / good days on which the condition held, plus up to 3 recent example dates."""
    x = rows[p["column"]]
    cond = (x < p["threshold"]) if p["op"] == "below" else (x > p["threshold"])
    out = dict(p)
    for kind in ("bad", "good"):
        days = (rows.label == kind) & x.notna()
        out[f"share_{kind}"] = (
            round(float((cond & days).sum() / days.sum()), 4) if days.any() else 0.0
        )
    hits = rows.date[cond & (rows.label == p["kind"])]
    out["example_dates"] = [str(d.date()) for d in hits.tail(3)]
    return out
