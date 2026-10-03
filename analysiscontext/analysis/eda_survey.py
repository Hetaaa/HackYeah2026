"""EDA on survey structure (questions 1-3) + completeness (4). Prints markdown tables.
Run after build_daily.py.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
from pathlib import Path

C = Path(__file__).resolve().parent / "cache"
sv = pd.read_csv(C / "survey.csv", parse_dates=["ts_local", "date"])
dl = pd.read_csv(C / "daily.csv", parse_dates=["ts_local", "date"])
fd = pd.read_csv(C / "fitbit_day.csv", parse_dates=["date"])
sl = pd.read_csv(C / "sleep_night.csv", parse_dates=["date"])
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)


def md(df, floatfmt=".2f"):
    print(df.to_markdown(floatfmt=floatfmt))
    print()


# ------------------------------------------------------------ Q1 time of day
print("## Q1 survey hour (local)")
g = sv.groupby("pid")
q1 = pd.DataFrame({
    "reports": g.size(),
    "days": g.date.nunique(),
    "multi_days": sv[sv.n_reports_day > 1].groupby("pid").date.nunique(),
    "hour_p10": g.hour.quantile(.1), "hour_med": g.hour.median(), "hour_p90": g.hour.quantile(.9),
    "pct_before10": g.hour.apply(lambda h: (h < 10).mean() * 100),
    "pct_10_12": g.hour.apply(lambda h: ((h >= 10) & (h < 12)).mean() * 100),
    "pct_12_18": g.hour.apply(lambda h: ((h >= 12) & (h < 18)).mean() * 100),
    "pct_18plus": g.hour.apply(lambda h: (h >= 18).mean() * 100),
}).fillna(0)
q1.loc["ALL"] = [len(sv), sv.groupby("pid").date.nunique().sum(), q1.multi_days.sum(),
                 sv.hour.quantile(.1), sv.hour.median(), sv.hour.quantile(.9),
                 (sv.hour < 10).mean() * 100, ((sv.hour >= 10) & (sv.hour < 12)).mean() * 100,
                 ((sv.hour >= 12) & (sv.hour < 18)).mean() * 100, (sv.hour >= 18).mean() * 100]
md(q1, ".1f")
hist = pd.cut(sv.hour, [0, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24], right=False).value_counts().sort_index()
md(hist.to_frame("n"))
# multi-report days: how different are the two reports? time gap
m = sv[sv.n_reports_day > 1].sort_values(["pid", "ts_local"])
gap = m.groupby(["pid", "date"]).ts_local.agg(lambda t: (t.max() - t.min()).total_seconds() / 3600)
same = m.groupby(["pid", "date"])[["mood", "fatigue", "stress"]].nunique().max(axis=1).eq(1)
print("multi-report days:", len(gap), "median gap h", gap.median(), "identical answers", same.sum())
md(m[["pid", "ts_local", "mood", "fatigue", "stress", "readiness"]].head(12))
# late reports vs sleep end: is survey after wake? (only main-sleep nights)
x = dl.merge(sl[["pid", "date", "end"]], on=["pid", "date"], how="left")
x["end"] = pd.to_datetime(x.end)
x["survey_minus_wake_h"] = (x.ts_local - x.end).dt.total_seconds() / 3600
print("survey before wake (survey_minus_wake<0):", (x.survey_minus_wake_h < 0).sum(), "of", x.survey_minus_wake_h.notna().sum())
print("survey - wake hours quantiles:", x.survey_minus_wake_h.quantile([.05, .25, .5, .75, .95]).round(2).to_dict())
# reports in the early night (00-05): maybe yesterday's report filed late
early = sv[sv.hour < 5]
print("reports 00-05 local:", len(early), early.groupby("pid").size().to_dict())

# ------------------------------------------------------------ Q2 direction
print("## Q2 Spearman among survey fields")
F = ["mood", "fatigue", "stress", "readiness", "soreness", "sleep_quality", "sleep_duration_h"]
d1 = dl.copy()
d1["readiness"] = d1.readiness.where(~d1.readiness_zero)  # check excluding suspicious zeros
z = d1.groupby("pid")[F].transform(lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) > 0 else s * np.nan)
md(z.corr(method="spearman"))
per = []
for pid, gg in d1.groupby("pid"):
    c = gg[F].corr(method="spearman")
    per.append(c.stack().rename(pid))
per = pd.concat(per, axis=1)
med = per.median(axis=1).unstack()
md(med.loc[F, F])
pos = (per > 0).sum(axis=1).unstack()
print("count of participants with positive rho:")
md(pos.loc[F, F], ".0f")

# readiness zeros
print("readiness==0 per pid:", sv[sv.readiness_zero].groupby("pid").size().to_dict())
rz = sv[sv.readiness_zero]
print("on readiness==0 days, mood distribution", rz.mood.value_counts().to_dict(), "fatigue", rz.fatigue.value_counts().to_dict())
print("invalid 0 in 1-5 fields:", sv[["mood", "fatigue", "stress", "soreness", "sleep_quality"]].isna().sum().to_dict())

# ------------------------------------------------------------ Q3 label
print("## Q3 label")


def zs(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd > 0 else s * 0.0


def composite(df, fields):
    zz = df.groupby("pid")[fields].transform(zs)
    comp = zz.mean(axis=1, skipna=True)
    comp[df[fields].notna().sum(axis=1) < len(fields) - (1 if len(fields) > 2 else 0)] = np.nan
    return comp.groupby(df.pid).transform(zs)


rows = []
for pid, gg in d1.groupby("pid"):
    raw3 = gg[["mood", "fatigue", "stress"]].mean(axis=1)
    raw4 = (gg[["mood", "fatigue", "stress"]].sum(axis=1) + gg.readiness / 2) / 4
    r = dict(pid=pid, n=len(gg),
             sd_mood=gg.mood.std(), sd_fatigue=gg.fatigue.std(), sd_stress=gg.stress.std(),
             sd_ready=gg.readiness.std(), sd_soreness=gg.soreness.std(),
             sd_raw3=raw3.std(),
             pct_all3=((gg.mood == 3) & (gg.fatigue == 3) & (gg.stress == 3)).mean() * 100,
             pct_mode_mood=gg.mood.value_counts(normalize=True).iloc[0] * 100,
             distinct_raw3=raw3.nunique())
    rows.append(r)
q3 = pd.DataFrame(rows).set_index("pid")
for name, fields in [("MFS", ["mood", "fatigue", "stress"]), ("MFSR", ["mood", "fatigue", "stress", "readiness"])]:
    comp = composite(d1, fields)
    lab = pd.cut(comp, [-np.inf, -0.5, 0.5, np.inf], labels=["bad", "neutral", "good"])
    ct = pd.crosstab(d1.pid, lab)
    q3[f"bad_{name}"] = ct["bad"]
    q3[f"good_{name}"] = ct["good"]
    d1[f"comp_{name}"] = comp
md(q3, ".2f")
print("corr MFS vs MFSR composite:", d1[["comp_MFS", "comp_MFSR"]].corr(method="spearman").iloc[0, 1])
d1[["pid", "date", "comp_MFS", "comp_MFSR"]].to_csv(C / "composite.csv", index=False)

# ------------------------------------------------------------ Q4 completeness
print("## Q4 completeness (final rules: wear-valid D-1, valid night ending D before survey)")
rows = []
for pid, gg in dl.groupby("pid"):
    f = fd[fd.pid == pid]
    s = sl[sl.pid == pid]
    lab = gg[["mood", "fatigue", "stress"]].notna().all(axis=1)
    sleepD = gg.sleep_h_lag1.notna()
    steps = gg.steps_lag1.notna()
    rhrN = gg.rhr_night_lag1.notna()
    rows.append(dict(pid=pid, survey_days=len(gg), label_ok=lab.sum(),
                     fitbit_days_worn=(f.wear_day >= 720).sum(),
                     main_sleep_nights=len(s), rhr_day_days=f.rhr_day.notna().sum(),
                     rhr_night_nights=s.rhr_night.notna().sum(),
                     S_sleep_D=sleepD.sum(), S_steps_Dm1_worn=steps.sum(),
                     S_rhr_day_Dm1=gg.rhr_day_lag1.notna().sum(), S_rhr_night_D=rhrN.sum(),
                     FULL=(lab & sleepD & steps).sum(),
                     FULL_rhr=(lab & sleepD & steps & rhrN).sum(),
                     FULL_preLockdown=(lab & sleepD & steps & (gg.date < "2020-03-12")).sum()))
q4 = pd.DataFrame(rows).set_index("pid")
q4.loc["SUM"] = q4.sum()
md(q4, ".0f")
