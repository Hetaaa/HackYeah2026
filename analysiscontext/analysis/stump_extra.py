"""Round 2: stump sanity check with extra features (round-1 stump_check.py logic, minority rule ON).

Configs:
  spec1    round-1 FINAL list (analiza-pmdata.md sec. 12 step 15)
  spec2    proposed round-2 final list: sleep_eff -> wake_pct (C), + rem_pct lag1 (G), + hr_sleep_mean lag1 (I)
  r1       round-1 stump grid (stump_check.GRID, lag1+avg3 for 9 features)  -> reproduces round 1
  r2       r1 + accepted new features (wake_pct lag1, rem_pct lag1, hr_sleep_mean lag1)
  r2_wide  r1 + every plausible new candidate incl. avg3 variants (stress test of multiple-testing cost)
  r1_watch r1 with srpe_load replaced by z_cardio_peak (watch-only training-load proxy)
For each pid x kind: best pattern, p_global, and the 95th percentile of the null max statistic (q95_null).
Output: cache/stump_extra.csv, printed summary.
"""
import warnings

import numpy as np
import pandas as pd

import HackYeah2026.analysiscontext.analysis.stump_check as sc
from HackYeah2026.analysiscontext.analysis.common import LOCKDOWN
from HackYeah2026.analysiscontext.analysis.eda_extra import load

warnings.filterwarnings("ignore")
sc.MINORITY = True
R1_GRID = dict(sc.GRID)
R1_VAR = dict(sc.VARIANTS)
NEW_GRID = {"wake_pct": ("above", 1), "rem_pct": ("below", 2), "hr_sleep_mean": ("above", 1),
            "deep_pct": ("below", 2), "z_cardio_peak": ("above", 10), "wake_long_n": ("above", 1)}
SPEC1_GRID = {k: R1_GRID[k] for k in ["sleep_h", "bedtime_h", "sleep_eff", "steps", "mvpa", "srpe_load", "lightly"]}
SPEC1_VAR = {"sleep_h": ["lag1", "avg3"], "bedtime_h": ["lag1", "avg3"], "sleep_eff": ["lag1"],
             "steps": ["lag1", "avg3"], "mvpa": ["lag1", "avg3"], "srpe_load": ["lag1", "avg3"],
             "lightly": ["lag1", "avg3"]}
SPEC2_GRID = {**{k: v for k, v in SPEC1_GRID.items() if k != "sleep_eff"},
              **{k: NEW_GRID[k] for k in ["wake_pct", "rem_pct", "hr_sleep_mean"]}}
SPEC2_VAR = {**{k: v for k, v in SPEC1_VAR.items() if k != "sleep_eff"},
             "wake_pct": ["lag1"], "rem_pct": ["lag1"], "hr_sleep_mean": ["lag1"]}
CONFIGS = {
    "spec1": (SPEC1_GRID, SPEC1_VAR),  # round-1 final list (sec. 12 step 15)
    "spec2": (SPEC2_GRID, SPEC2_VAR),  # proposed round-2 final list
    "r1": (R1_GRID, R1_VAR),
    "r2": ({**R1_GRID, **{k: NEW_GRID[k] for k in ["wake_pct", "rem_pct", "hr_sleep_mean"]}},
           {**R1_VAR, "wake_pct": ["lag1"], "rem_pct": ["lag1"], "hr_sleep_mean": ["lag1"]}),
    "r2_wide": ({**R1_GRID, **NEW_GRID},
                {**R1_VAR, **{k: ["lag1", "avg3"] for k in NEW_GRID}}),
    "r1_watch": ({**{k: v for k, v in R1_GRID.items() if k != "srpe_load"}, "z_cardio_peak": NEW_GRID["z_cardio_peak"]},
                 {**{k: v for k, v in R1_VAR.items() if k != "srpe_load"}, "z_cardio_peak": ["lag1", "avg3"]}),
}


def run(g, kind):
    y = (g.label == kind).to_numpy()
    conds = sc.build_conditions(g, kind)
    if not conds:
        return None, None
    obs = sc.score_all(conds, y)
    feats = np.array([c[0] + "_" + c[1] for c in conds])
    ufeat = np.unique(feats)
    max_all, max_feat = [], {f: [] for f in ufeat}
    for k in range(14, len(y) - 13):
        s = sc.score_all(conds, np.roll(y, k))
        max_all.append(s.max())
        for f in ufeat:
            max_feat[f].append(s[feats == f].max())
    max_all = np.array(max_all)
    rows = []
    for f in ufeat:
        idx = np.where(feats == f)[0]
        i = idx[np.argmax(obs[idx])]
        fname, v, dirn, thr, cond, ok = conds[i]
        rows.append(dict(kind=kind, feature=f, dir=dirn, thr=thr, n_in=int(cond.sum()), k_in=int(y[cond].sum()),
                         rate_in=y[cond].mean(), rate_out=y[ok & ~cond].mean(), score=obs[i],
                         p_global=(max_all >= obs[i]).mean(), p_feature=(np.array(max_feat[f]) >= obs[i]).mean()))
    meta = dict(n_conds=len(conds), n_featvars=len(ufeat), q95_null=np.quantile(max_all, .95))
    return pd.DataFrame(rows).sort_values("score", ascending=False), meta


def main(prelock=False):
    d = load()
    if prelock:
        d = d[d.date < LOCKDOWN]
    res, metas = [], []
    for cfg, (grid, var) in CONFIGS.items():
        sc.GRID, sc.VARIANTS = grid, var
        for pid, g in d.groupby("pid"):
            g = g.sort_values("date")
            g = g[g.sleep_h_lag1.notna() | g.steps_lag1.notna()]
            for kind in ["bad", "good"]:
                if (g.label == kind).sum() < 10:
                    continue
                r, meta = run(g, kind)
                if r is None:
                    continue
                r.insert(0, "pid", pid)
                r.insert(0, "config", cfg)
                res.append(r)
                metas.append(dict(config=cfg, pid=pid, kind=kind, n_label=int((g.label == kind).sum()), **meta))
    R = pd.concat(res)
    M = pd.DataFrame(metas)
    tag = "_prelock" if prelock else ""
    R.to_csv(sc.CACHE / f"stump_extra{tag}.csv", index=False)
    M.to_csv(sc.CACHE / f"stump_extra_meta{tag}.csv", index=False)
    return R, M


def summary(R, M):
    rows = []
    for (cfg, pid, kind), g in R.groupby(["config", "pid", "kind"]):
        top = g.iloc[0]
        sig = g[g.p_global < .05]
        rows.append(dict(config=cfg, pid=pid, kind=kind, best=f"{top.feature} {top.dir} {top.thr}",
                         k_in=f"{top.k_in}/{top.n_in}", rate_in=top.rate_in, rate_out=top.rate_out,
                         p_global=top.p_global, n_sig=len(sig), sig=", ".join(sig.feature.head(5))))
    S = pd.DataFrame(rows).merge(M, on=["config", "pid", "kind"])
    return S


if __name__ == "__main__":
    import sys
    pre = "--prelock" in sys.argv
    R, M = main(prelock=pre)
    S = summary(R, M)
    pd.set_option("display.width", 300)
    piv = S.pivot_table(index=["pid", "kind"], columns="config", values=["p_global", "n_sig", "q95_null", "n_featvars"],
                        aggfunc="first")
    print(piv.round(3).to_markdown())
    print()
    print(S.sort_values(["pid", "kind", "config"]).to_markdown(index=False, floatfmt=".2f"))
