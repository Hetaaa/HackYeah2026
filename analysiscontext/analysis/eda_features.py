"""EDA questions 5-9 (structure only, no label): non-wear, feature coverage, collinearity, ranges, trends."""
import warnings

import numpy as np
import pandas as pd

from HackYeah2026.analysiscontext.analysis.common import CACHE, LOCKDOWN, load_daily, label_median

warnings.filterwarnings("ignore")
HERE = CACHE.parent
d = load_daily()
fd = pd.read_csv(CACHE / "fitbit_day.csv", parse_dates=["date"])
sl = pd.read_csv(CACHE / "sleep_night.csv", parse_dates=["date"])


def md(df, f=".2f"):
    print(df.to_markdown(floatfmt=f))
    print()


# ---------------------------------------------------------------- Q5 non-wear per participant (survey days, D-1)
print("## Q5 non-wear on D-1 among survey days with main sleep D")
base = d[d.sleep_h_lag1.notna()]
rows = []
for pid, g in base.groupby("pid"):
    rows.append(dict(pid=pid, n_sleepD=len(g),
                     no_hr_file_day=(g.wear_min_dm1.fillna(0) == 0).sum(),
                     rule_sed1400=(g.sedentary_raw_dm1 >= 1400).sum(),
                     rule_total_lt1000=(g.wear_min_dm1.fillna(0) < 1000).sum(),
                     rule_day_lt720=(g.wear_day_dm1 < 720).sum(),
                     rule_day_lt600=(g.wear_day_dm1 < 600).sum(),
                     kept_day720=(g.wear_day_dm1 >= 720).sum()))
q5 = pd.DataFrame(rows).set_index("pid")
q5.loc["SUM"] = q5.sum()
md(q5, ".0f")

# ---------------------------------------------------------------- Q6 coverage
print("## Q6 coverage of RHR and training-load sources (survey days)")
sr = []
for pid in sorted(d.pid.unique()):
    s = pd.read_csv(HERE.parent / "pmdata" / pid / "pmsys" / "srpe.csv")
    sr.append(dict(pid=pid, srpe_sessions=len(s)))
sr = pd.DataFrame(sr).set_index("pid")
rows = []
for pid, g in d.groupby("pid"):
    f = fd[fd.pid == pid]
    s = sl[sl.pid == pid]
    both = g[["rhr_day_lag1", "rhr_night_lag1"]].dropna()
    fdd = f.set_index("date")
    # same-night agreement: rhr_day of D-1 vs rhr_night of night ending D
    rows.append(dict(pid=pid, survey_days=len(g),
                     rhr_day_Dm1=g.rhr_day_lag1.notna().sum(), rhr_night_D=g.rhr_night_lag1.notna().sum(),
                     rho_day_vs_night=both.corr("spearman").iloc[0, 1] if len(both) > 10 else np.nan,
                     mean_diff_bpm=(both.rhr_night_lag1 - both.rhr_day_lag1).mean() if len(both) else np.nan,
                     srpe_sessions=sr.loc[pid, "srpe_sessions"],
                     srpe_days=(f.srpe_load > 0).sum(),
                     srpe_Dm1_pos=(g.srpe_load_lag1 > 0).sum(),
                     ex_days=(f.ex_min > 0).sum(), ex_nonwalk_days=(f.ex_min_nonwalk > 0).sum(),
                     ex_nonwalk_Dm1=(g.ex_min_nonwalk_lag1 > 0).sum()))
md(pd.DataFrame(rows).set_index("pid"), ".2f")
print("sleep type classic share (efficiency defined differently):", (sl.type == "classic").mean())
print(sl.groupby("type").sleep_eff.describe())
print("nights with 2+ main sleeps:", (sl.n_main_sleeps > 1).sum())

# ---------------------------------------------------------------- Q7 collinearity
print("## Q7 feature-feature Spearman (lag1 aligned on survey day; wear-filtered)")
F = ["sleep_h", "time_in_bed_h", "sleep_eff", "bedtime_h", "rhr_night", "rhr_day", "steps", "distance_km",
     "calories", "lightly", "moderately", "very", "mvpa", "active_total", "sedentary", "srpe_load", "ex_min"]
cols = [f + "_lag1" for f in F]
X = d[["pid"] + cols].copy()
excl = ["p12", "p13", "p03"]
X = X[~X.pid.isin(excl)]
Z = X.groupby("pid")[cols].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
pooled = Z.corr("spearman")
pooled.index = pooled.columns = F
md(pooled, ".2f")
per = [g[cols].corr("spearman").stack().rename(p) for p, g in X.groupby("pid")]
med = pd.concat(per, axis=1).median(axis=1).unstack().loc[cols, cols]
med.index = med.columns = F
md(med, ".2f")
print("lag1 vs avg3 Spearman (pooled within-person):")
r = {}
for f in ["sleep_h", "sleep_eff", "bedtime_h", "rhr_night", "rhr_day", "steps", "lightly", "mvpa", "sedentary"]:
    zz = d[~d.pid.isin(excl)].groupby("pid")[[f + "_lag1", f + "_avg3"]].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0))
    r[f] = zz.corr("spearman").iloc[0, 1]
print(pd.Series(r).round(2).to_dict())
# share of between-person variance (ICC-like) per feature
print("between-person variance share (ICC-like):")
icc = {}
for f in ["sleep_h", "bedtime_h", "rhr_day", "rhr_night", "steps", "mvpa", "lightly", "sedentary"]:
    c = f + "_lag1"
    y = X[["pid", c]].dropna()
    icc[f] = y.groupby("pid")[c].mean().var() / y[c].var()
print(pd.Series(icc).round(2).to_dict())

# ---------------------------------------------------------------- Q8 ranges
print("## Q8 ranges (lag1, survey days, wear-filtered, excl p03/p12/p13)")
rows = []
for f in ["sleep_h", "time_in_bed_h", "sleep_eff", "bedtime_h", "rhr_night", "rhr_day", "steps", "lightly",
          "moderately", "very", "mvpa", "sedentary", "srpe_load"]:
    v = X[f + "_lag1"] if f + "_lag1" in X else d[f + "_lag1"]
    within = X.groupby("pid")[f + "_lag1"].agg(lambda s: s.quantile(.9) - s.quantile(.1))
    rows.append(dict(feature=f, n=v.notna().sum(), p01=v.quantile(.01), p10=v.quantile(.1), p50=v.median(),
                     p90=v.quantile(.9), p99=v.quantile(.99), within_p10_p90_median=within.median(),
                     within_min=within.min(), within_max=within.max()))
md(pd.DataFrame(rows).set_index("feature"), ".1f")
# outliers
print("sleep_h<3:", (sl.sleep_h < 3).sum(), "sleep_h>11:", (sl.sleep_h > 11).sum(),
      "bedtime outside 18-06 (h<0 or >12):", ((sl.bedtime_h < 0) | (sl.bedtime_h > 12)).sum())
print("steps>40000 days:", (fd.steps > 40000).sum(), "rhr_day<35 or >100:", ((fd.rhr_day < 35) | (fd.rhr_day > 100)).sum())
print(sl[(sl.bedtime_h < 0) | (sl.bedtime_h > 12)][["pid", "date", "start", "end", "sleep_h"]].head(10))

# ---------------------------------------------------------------- Q9 trends
print("## Q9 trends")
d["comp"] = label_median(d)
d["month"] = d.date.dt.to_period("M")
fdw = fd[fd.wear_day >= 720].copy()
fdw["month"] = fdw.date.dt.to_period("M")
fdw["rel"] = fdw.steps / fdw.groupby("pid").steps.transform("median")
print("pooled steps relative to person median, per month:")
print(fdw.groupby("month").rel.median().round(2).to_dict())
print("pooled composite (median-centred z) per month:")
print(d.groupby("month").comp.mean().round(2).to_dict())
hol = (fdw.date >= "2019-12-21") & (fdw.date <= "2020-01-01")
rows = []
for pid, g in fdw.groupby("pid"):
    dd = d[d.pid == pid]
    pre = g[g.date < LOCKDOWN]
    post = g[g.date >= LOCKDOWN]
    gh = (g.date >= "2019-12-21") & (g.date <= "2020-01-01")
    rows.append(dict(pid=pid,
                     steps_rho_time=g[["steps"]].assign(t=g.date.rank()).corr("spearman").iloc[0, 1],
                     steps_pre=pre.steps.median(), steps_post=post.steps.median(), n_post=len(post),
                     steps_holiday_ratio=g[gh].steps.median() / g[~gh].steps.median(),
                     comp_rho_time=dd[["comp"]].assign(t=dd.date.rank()).corr("spearman").iloc[0, 1],
                     comp_post_minus_pre=dd[dd.date >= LOCKDOWN].comp.mean() - dd[dd.date < LOCKDOWN].comp.mean(),
                     n_survey_post=(dd.date >= LOCKDOWN).sum(),
                     weekend_steps_ratio=g[g.date.dt.dayofweek >= 5].steps.median() / g[g.date.dt.dayofweek < 5].steps.median()))
md(pd.DataFrame(rows).set_index("pid"), ".2f")
print("survey days per month:", d.groupby("month").size().to_dict())
print("survey last date per pid:", d.groupby("pid").date.max().dt.date.astype(str).to_dict())

# plot
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pids = sorted(d.pid.unique())
    fig, axes = plt.subplots(len(pids), 1, figsize=(11, 1.6 * len(pids)), sharex=True)
    for ax, pid in zip(axes, pids):
        g = fdw[fdw.pid == pid].set_index("date").steps.rolling("7D").median()
        ax.plot(g.index, g / 1000, color="#3b6ea5", lw=1)
        ax.set_ylabel(pid, rotation=0, labelpad=18)
        ax2 = ax.twinx()
        c = d[d.pid == pid].set_index("date").comp.rolling("7D").mean()
        ax2.plot(c.index, c, color="#c2703d", lw=1)
        ax2.axhline(0, color="#ccc", lw=.5)
        ax.axvline(LOCKDOWN, color="k", ls="--", lw=.7)
        ax.axvspan(pd.Timestamp("2019-12-21"), pd.Timestamp("2020-01-01"), color="#eee")
    axes[0].set_title("7-day median steps [k] (blue) and 7-day mean wellness composite (orange); dashed = 2020-03-12")
    fig.tight_layout()
    (HERE / "plots").mkdir(exist_ok=True)
    fig.savefig(HERE / "plots" / "trends.png", dpi=90)
    print("plot saved")
except ImportError:
    pass
