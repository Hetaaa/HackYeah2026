"""Persona ranking for all participants + detailed tables for chosen personas."""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from HackYeah2026.analysiscontext.analysis.common import CACHE, LOCKDOWN

warnings.filterwarnings("ignore")
d = pd.read_csv(CACHE / "analysis_table.csv", parse_dates=["date"])
R = pd.read_csv(CACHE / "corr_person.csv")
S = pd.read_csv(CACHE / "stump_check_median_minority.csv")
dl = pd.read_csv(CACHE / "daily.csv")

rows = []
for pid in sorted(dl.pid.unique()):
    g = d[d.pid == pid]
    full = g[g.sleep_h_lag1.notna() & g.steps_lag1.notna()]
    rc = R[(R.pid == pid) & (R.target == "comp") & ~R.feature.str.contains("dev28|time_in_bed|rhr_day|ex_min")]
    top = rc.loc[rc.rho.abs().idxmax()] if len(rc) else None
    s = S[S.pid == pid]
    sig = s[s.p_global < .05]
    rows.append(dict(pid=pid, full_days=len(full), sd_raw=g[["mood", "fatigue", "stress"]].mean(axis=1).std(),
                     bad=(full.label == "bad").sum(), good=(full.label == "good").sum(),
                     top_feature=None if top is None else top.feature, top_rho=None if top is None else top.rho,
                     top_q=None if top is None else top.q_bh, n_q10=(rc.q_bh < .10).sum(),
                     stump_sig=", ".join(f"{r.kind}:{r.feature} {r.dir} {r.thr:g}" for r in sig.itertuples()),
                     post_lock_days=(full.date >= LOCKDOWN).sum()))
T = pd.DataFrame(rows).set_index("pid")
print(T.to_markdown(floatfmt=".2f"))

# component check: which survey field drives the sleep association (pooled within-person)
print("\n## components: pooled within-person Spearman of sleep_h_lag1 / srpe_load_lag1 / lightly_lag1 with each field")
for f in ["sleep_h_lag1", "srpe_load_lag1", "lightly_lag1", "steps_lag1"]:
    out = {}
    for t in ["mood", "fatigue", "stress", "readiness", "soreness", "comp"]:
        sub = d[["pid", f, t]].dropna()
        z = sub.groupby("pid")[[f, t]].transform(lambda s: (s - s.mean()) / s.std(ddof=0)).dropna()
        out[t] = round(stats.spearmanr(z[f], z[t])[0], 3)
    print(f, out)


def persona(pid, feats):
    g = d[d.pid == pid].copy()
    print(f"\n## {pid}: n={len(g)}, bad={(g.label == 'bad').sum()}, good={(g.label == 'good').sum()}, "
          f"neutral={(g.label == 'neutral').sum()}, period {g.date.min().date()}..{g.date.max().date()}")
    rows = []
    for f, thr, dirn in feats:
        x = g[f]
        ok = x.notna() & g.label.notna()
        cond = (x < thr) if dirn == "below" else (x > thr)
        cin, cout = ok & cond, ok & ~cond
        rr = R[(R.pid == pid) & (R.feature == f)]
        rc = rr[rr.target == "comp"].iloc[0]
        rm = rr[rr.target == "mood"].iloc[0]
        rows.append(dict(feature=f, rule=f"{dirn} {thr:g}", rho_comp=rc.rho, p_eff=rc.p_eff, q=rc.q_bh,
                         rho_mood=rm.rho, rho_weekday=rc.rho_weekday, rho_prelock=rc.rho_prelock,
                         rho_partial=rc.rho_partial, n=int(ok.sum()),
                         med_bad=x[g.label == "bad"].median(), med_neutral=x[g.label == "neutral"].median(),
                         med_good=x[g.label == "good"].median(),
                         days_in=int(cin.sum()),
                         bad_in=f"{int((g.label[cin] == 'bad').sum())}/{int(cin.sum())}",
                         bad_rate_in=(g.label[cin] == "bad").mean(), bad_rate_out=(g.label[cout] == "bad").mean(),
                         good_rate_in=(g.label[cin] == "good").mean(), good_rate_out=(g.label[cout] == "good").mean()))
    print(pd.DataFrame(rows).to_markdown(index=False, floatfmt=".2f"))
    # descriptive
    print("medians:", g[["sleep_h_lag1", "bedtime_h_lag1", "steps_lag1", "lightly_lag1", "mvpa_lag1", "rhr_night_lag1",
                         "srpe_load_lag1", "hour"]].median().round(2).to_dict())
    print("survey fields share of mode:", {c: round(g[c].value_counts(normalize=True).iloc[0], 2) for c in ["mood", "fatigue", "stress"]})


persona("p06", [("sleep_h_lag1", 6.5, "below"), ("sleep_h_avg3", 6.5, "below"), ("sleep_h_lag1", 6.0, "below"),
                ("bedtime_h_lag1", 6.5, "above"), ("time_in_bed_h_lag1", 7.0, "below"), ("steps_lag1", 12000, "below")])
persona("p01", [("srpe_load_lag1", 0, "above"), ("srpe_load_lag1", 300, "above"), ("ex_min_nonwalk_lag1", 0, "above"),
                ("rhr_night_avg3", 52, "above"), ("sleep_h_lag1", 6.5, "below"), ("lightly_lag1", 200, "below"),
                ("steps_avg3", 12000, "below")])
persona("p10", [("sleep_h_lag1", 7.0, "below"), ("sleep_h_lag1", 6.5, "below"), ("lightly_avg3", 260, "below"),
                ("lightly_lag1", 250, "below"), ("steps_lag1", 10000, "below"), ("sleep_eff_lag1", 94, "below")])
persona("p16", [("sleep_h_lag1", 6.0, "below"), ("sleep_h_lag1", 5.5, "below"), ("steps_avg3", 2000, "below"),
                ("steps_lag1", 2000, "below"), ("lightly_lag1", 100, "below"), ("bedtime_h_lag1", 13, "above")])
persona("p04", [("bedtime_h_avg3", 6.0, "above"), ("bedtime_h_lag1", 6.0, "above"), ("sleep_eff_avg3", 93, "below"),
                ("sleep_h_lag1", 7.0, "below"), ("steps_lag1", 10000, "below")])
persona("p08", [("sleep_h_avg3", 7.0, "below"), ("sleep_h_lag1", 7.0, "below"), ("steps_lag1", 12000, "below")])
persona("p09", [("sleep_h_lag1", 7.0, "below"), ("sedentary_avg3", 750, "above"), ("steps_lag1", 5000, "below")])
