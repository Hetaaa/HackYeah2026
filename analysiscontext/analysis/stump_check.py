"""Sanity check of the planned threshold+lift ('stump') algorithm with circular-shift permutation test.
Implements koncepcja-analityczna 2.2/2.3 in a simplified way (median-centred label, a-priori directions).
NOT the production implementation - used only to see which participants would yield patterns.
"""
import warnings

import numpy as np
import pandas as pd

from HackYeah2026.analysiscontext.analysis.common import CACHE, LOCKDOWN

warnings.filterwarnings("ignore")
MIN_SUPPORT = 10
MINORITY = False  # if True: condition must cover <= 50% of days (avoids 'out = 10 extreme days' artefacts)
Z95 = 1.96
# feature: (direction of BAD condition: 'below'/'above', grid step)
GRID = {
    "sleep_h": ("below", 0.5), "sleep_eff": ("below", 1), "bedtime_h": ("above", 0.5),
    "rhr_night": ("above", 1), "steps": ("below", 1000), "lightly": ("below", 20), "mvpa": ("below", 10),
    "sedentary": ("above", 30), "srpe_load": ("above", 100),
}
VARIANTS = {"sleep_h": ["lag1", "avg3"], "sleep_eff": ["lag1", "avg3"], "bedtime_h": ["lag1", "avg3"],
            "rhr_night": ["lag1", "avg3"], "steps": ["lag1", "avg3"], "lightly": ["lag1", "avg3"],
            "mvpa": ["lag1", "avg3"], "sedentary": ["lag1", "avg3"], "srpe_load": ["lag1", "avg3"]}


def wilson_lower(k, n):
    p = k / n
    den = 1 + Z95 ** 2 / n
    c = p + Z95 ** 2 / (2 * n)
    a = Z95 * np.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n))
    return (c - a) / den


def build_conditions(g, kind):
    conds = []
    for f, (dirn, step) in GRID.items():
        if kind == "good":
            dirn = "above" if dirn == "below" else "below"
        for v in VARIANTS[f]:
            c = f"{f}_{v}"
            x = g[c].to_numpy(float)
            ok = ~np.isnan(x)
            if ok.sum() < 2 * MIN_SUPPORT:
                continue
            lo, hi = np.nanquantile(x, [0.05, 0.95])
            for thr in np.arange(np.floor(lo / step) * step, hi + step, step):
                cond = (x < thr) if dirn == "below" else (x > thr)
                cond = cond & ok
                nin, nout = cond.sum(), (ok & ~cond).sum()
                if nin < MIN_SUPPORT or nout < MIN_SUPPORT:
                    continue
                if MINORITY and nin > 0.5 * ok.sum():
                    continue
                conds.append((f, v, dirn, round(float(thr), 2), cond, ok))
    return conds


def score_all(conds, y):
    out = np.empty(len(conds))
    for i, (_, _, _, _, cond, ok) in enumerate(conds):
        nin = cond.sum()
        kin = y[cond].sum()
        rest = ok & ~cond
        out[i] = wilson_lower(kin, nin) - y[rest].mean()
    return out


def run(g, kind):
    y = (g.label == kind).to_numpy()
    conds = build_conditions(g, kind)
    if not conds:
        return None
    obs = score_all(conds, y)
    n = len(y)
    shifts = range(14, n - 13)
    feats = np.array([c[0] + "_" + c[1] for c in conds])
    ufeat = np.unique(feats)
    max_all, max_feat = [], {f: [] for f in ufeat}
    for k in shifts:
        s = score_all(conds, np.roll(y, k))
        max_all.append(s.max())
        for f in ufeat:
            max_feat[f].append(s[feats == f].max())
    max_all = np.array(max_all)
    rows = []
    for f in ufeat:
        idx = np.where(feats == f)[0]
        i = idx[np.argmax(obs[idx])]
        fname, v, dirn, thr, cond, ok = conds[i]
        mf = np.array(max_feat[f])
        rows.append(dict(kind=kind, feature=f, dir=dirn, thr=thr, n_in=int(cond.sum()),
                         k_in=int(y[cond].sum()), rate_in=y[cond].mean(), rate_out=y[ok & ~cond].mean(),
                         score=obs[i], p_global=(max_all >= obs[i]).mean(), p_feature=(mf >= obs[i]).mean()))
    return pd.DataFrame(rows).sort_values("score", ascending=False)


def main(exclude_post=False, label="median"):
    d = pd.read_csv(CACHE / "analysis_table.csv", parse_dates=["date"])
    if label == "spec":
        from HackYeah2026.analysiscontext.analysis.common import label_spec, to_label
        d["label"] = to_label(label_spec(d))
    if exclude_post:
        d = d[d.date < LOCKDOWN]
    res = []
    for pid, g in d.groupby("pid"):
        g = g.sort_values("date")
        g = g[g.sleep_h_lag1.notna() | g.steps_lag1.notna()]
        for kind in ["bad", "good"]:
            if (g.label == kind).sum() < 10:
                continue
            r = run(g, kind)
            if r is not None:
                r.insert(0, "pid", pid)
                r["n_days"] = len(g)
                r["n_label"] = int((g.label == kind).sum())
                res.append(r)
    R = pd.concat(res)
    tag = ("_prelock" if exclude_post else "") + f"_{label}" + ("_minority" if MINORITY else "")
    R.to_csv(CACHE / f"stump_check{tag}.csv", index=False)
    return R


if __name__ == "__main__":
    import sys
    MINORITY = "--minority" in sys.argv
    globals()["MINORITY"] = MINORITY
    R = main(exclude_post="--prelock" in sys.argv, label="spec" if "--spec" in sys.argv else "median")
    pd.set_option("display.width", 250)
    summ = []
    for (pid, kind), g in R.groupby(["pid", "kind"]):
        top = g.iloc[0]
        summ.append(dict(pid=pid, kind=kind, n_days=top.n_days, n_label=top.n_label,
                         best=f"{top.feature} {top.dir} {top.thr}", k_in=f"{top.k_in}/{top.n_in}",
                         rate_in=top.rate_in, rate_out=top.rate_out, score=top.score, p_global=top.p_global,
                         n_sig_global=(g.p_global < .05).sum(), n_prelim=(g.p_feature < .05).sum(),
                         prelim=", ".join(g[g.p_feature < .05].feature.head(4))))
    print(pd.DataFrame(summ).to_markdown(index=False, floatfmt=".2f"))
