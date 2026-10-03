"""Feature -> wellness correlations (only pre-survey data, aligned per build_daily rules).

Targets: mood (raw 1-5) and composite (mood+fatigue+stress, person-standardised; Spearman is invariant to
median vs mean centring). Per participant + pooled within-person.
Significance: Spearman p with effective n (Bartlett: n_eff = n (1 - r1x r1y)/(1 + r1x r1y)),
BH-FDR within participant x target. Confounder checks: weekdays only (D in Tue-Fri), pre-lockdown only,
partial rank correlation controlling weekend(D-1), post-lockdown, linear time.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from HackYeah2026.analysiscontext.analysis.common import CACHE, LOCKDOWN, label_median, load_daily, to_label

warnings.filterwarnings("ignore")

FEATS = ["sleep_h", "time_in_bed_h", "sleep_eff", "bedtime_h", "rhr_night", "rhr_day", "steps", "lightly", "mvpa",
         "sedentary", "srpe_load", "ex_min_nonwalk"]
DEV = ["steps_dev28", "mvpa_dev28", "sleep_h_dev28"]
EXCL = ["p12"]  # no sleep at all
MIN_N = 30


def add_dev28(d):
    """Deviation of D-1 activity (and night D sleep) from the person's rolling 28-day median of PREVIOUS days."""
    fd = pd.read_csv(CACHE / "fitbit_day.csv", parse_dates=["date"])
    sl = pd.read_csv(CACHE / "sleep_night.csv", parse_dates=["date"])
    out = []
    for pid, g in d.groupby("pid"):
        f = fd[fd.pid == pid].set_index("date").sort_index()
        f = f.reindex(pd.date_range(f.index.min(), f.index.max()))
        valid = f.wear_day >= 720
        res = {}
        for c in ["steps", "mvpa"]:
            s = f[c].where(valid)
            base = s.shift(1).rolling(28, min_periods=14).median()  # days before the feature day
            res[c] = (s - base)
        s = sl[sl.pid == pid].set_index("date").sleep_h.sort_index()
        if len(s):
            s = s.reindex(pd.date_range(s.index.min(), s.index.max()))
            res["sleep_h"] = s - s.shift(1).rolling(28, min_periods=14).median()
        D = g.date
        gg = g[["pid", "date"]].copy()
        gg["steps_dev28_lag1"] = res["steps"].reindex(D - pd.Timedelta(days=1)).to_numpy()
        gg["mvpa_dev28_lag1"] = res["mvpa"].reindex(D - pd.Timedelta(days=1)).to_numpy()
        gg["sleep_h_dev28_lag1"] = res["sleep_h"].reindex(D).to_numpy() if "sleep_h" in res else np.nan
        out.append(gg)
    x = pd.concat(out)
    d = d.merge(x, on=["pid", "date"], how="left")
    d.loc[d.sleep_h_lag1.isna(), "sleep_h_dev28_lag1"] = np.nan
    return d


def r1(x):
    x = pd.Series(np.asarray(x, float))
    return x.autocorr(1) if len(x) > 5 else 0.0


def spearman_eff(x, y):
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    n = len(x)
    if n < 10 or np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return np.nan, n, np.nan, np.nan, np.nan
    rho, p = stats.spearmanr(x, y)
    rx, ry = stats.rankdata(x), stats.rankdata(y)
    a, b = max(r1(rx), 0), max(r1(ry), 0)
    neff = n * (1 - a * b) / (1 + a * b)
    t = rho * np.sqrt((neff - 2) / max(1e-9, 1 - rho ** 2))
    peff = 2 * stats.t.sf(abs(t), neff - 2)
    return rho, n, p, peff, neff


def bh(p):
    p = np.asarray(p, float)
    q = np.full_like(p, np.nan)
    m = ~np.isnan(p)
    if m.sum() == 0:
        return q
    pv = p[m]
    order = np.argsort(pv)
    ranked = pv[order] * m.sum() / (np.arange(m.sum()) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(pv)
    out[order] = np.minimum(ranked, 1)
    q[m] = out
    return q


def partial_rank(x, y, Z):
    m = ~(np.isnan(x) | np.isnan(y) | np.isnan(Z).any(axis=1))
    if m.sum() < 20:
        return np.nan
    xr, yr = stats.rankdata(x[m]), stats.rankdata(y[m])
    Zm = np.column_stack([np.ones(m.sum()), Z[m]])
    rx = xr - Zm @ np.linalg.lstsq(Zm, xr, rcond=None)[0]
    ry = yr - Zm @ np.linalg.lstsq(Zm, yr, rcond=None)[0]
    return np.corrcoef(rx, ry)[0, 1]


def main():
    d = load_daily()
    d = d[~d.pid.isin(EXCL)].copy()
    d = d[d[["mood", "fatigue", "stress"]].notna().all(axis=1)].sort_values(["pid", "date"])
    d["comp"] = label_median(d)
    d["label"] = to_label(d.comp)
    d = add_dev28(d)
    d["weekend_dm1"] = (d.date - pd.Timedelta(days=1)).dt.dayofweek >= 5
    d["weekday_clean"] = d.date.dt.dayofweek.between(1, 4)  # Tue-Fri: D and D-1 are weekdays
    d["post"] = d.date >= LOCKDOWN
    d["t"] = (d.date - d.date.min()).dt.days
    cols = [f"{f}_{v}" for f in FEATS for v in ("lag1", "avg3")] + [f"{c}_lag1" for c in DEV]

    rows = []
    for pid, g in d.groupby("pid"):
        for target in ["comp", "mood"]:
            y = g[target].to_numpy(float)
            for c in cols:
                x = g[c].to_numpy(float)
                rho, n, p, peff, neff = spearman_eff(x, y)
                if n < MIN_N:
                    continue
                Z = g[["weekend_dm1", "post", "t"]].to_numpy(float)
                wk = g.weekday_clean.to_numpy()
                pre = ~g.post.to_numpy()
                rows.append(dict(pid=pid, target=target, feature=c, rho=rho, n=n, p=p, p_eff=peff, n_eff=neff,
                                 rho_weekday=spearman_eff(x[wk], y[wk])[0], n_weekday=int((wk & ~np.isnan(x)).sum()),
                                 rho_prelock=spearman_eff(x[pre], y[pre])[0],
                                 rho_partial=partial_rank(x, y, Z)))
    R = pd.DataFrame(rows)
    R["q_bh"] = np.nan
    for (pid, t), idx in R.groupby(["pid", "target"]).groups.items():
        R.loc[idx, "q_bh"] = bh(R.loc[idx, "p_eff"])
    R.to_csv(CACHE / "corr_person.csv", index=False)

    # pooled within-person
    pooled = []
    for target in ["comp", "mood"]:
        for c in cols:
            sub = d[["pid", c, target]].dropna()
            sub = sub[sub.groupby("pid")[c].transform("size") >= MIN_N]
            zz = sub.groupby("pid")[[c, target]].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
            zz = zz.dropna()
            rho, p = stats.spearmanr(zz[c], zz[target]) if len(zz) > 30 else (np.nan, np.nan)
            pr = R[(R.target == target) & (R.feature == c)]
            tt = stats.ttest_1samp(pr.rho.dropna(), 0) if len(pr) > 2 else None
            pooled.append(dict(target=target, feature=c, rho_pooled=rho, n=len(zz), persons=len(pr),
                               mean_rho=pr.rho.mean(), median_rho=pr.rho.median(), n_pos=(pr.rho > 0).sum(),
                               n_sig=((pr.p_eff < .05)).sum(), n_q10=(pr.q_bh < .10).sum(),
                               p_between_persons=tt.pvalue if tt else np.nan))
    P = pd.DataFrame(pooled)
    P.to_csv(CACHE / "corr_pooled.csv", index=False)

    # bad vs good medians (median-centred label)
    bg = []
    for c in cols:
        for pid, g in d.groupby("pid"):
            b = g.loc[g.label == "bad", c].dropna()
            gd = g.loc[g.label == "good", c].dropna()
            nn = g.loc[g.label == "neutral", c].dropna()
            if len(b) >= 8 and len(gd) >= 8:
                u = stats.mannwhitneyu(b, gd)
                bg.append(dict(pid=pid, feature=c, n_bad=len(b), n_good=len(gd), med_bad=b.median(),
                               med_neutral=nn.median(), med_good=gd.median(), p_mw=u.pvalue))
    BG = pd.DataFrame(bg)
    BG.to_csv(CACHE / "bad_good_medians.csv", index=False)

    # autocorrelation of composite per person
    ac = d.groupby("pid").comp.apply(lambda s: s.autocorr(1)).round(2)
    print("lag-1 autocorrelation of composite (consecutive survey rows):", ac.to_dict())
    d.to_csv(CACHE / "analysis_table.csv", index=False)
    return d, R, P, BG


if __name__ == "__main__":
    d, R, P, BG = main()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    print("## pooled within-person, composite")
    print(P[P.target == "comp"].drop(columns="target").to_markdown(index=False, floatfmt=".3f"))
    print("## pooled within-person, mood")
    print(P[P.target == "mood"].drop(columns="target").to_markdown(index=False, floatfmt=".3f"))
