"""Round 2 EDA of extra watch-only features (cache/extra_features.csv from build_extra.py).

Sections (printed as markdown to stdout; run with  > cache/eda_extra.out.md):
  A  quality / coverage / plausibility (12 kept participants)
  B  redundancy: within-person Spearman (z per person pooled + per-person median), old + new features
  C  lag1 vs avg3 similarity
  D  feature -> target (INFORMATION ONLY): per person + pooled, p_eff, BH-FDR
Outputs: cache/extra_ff_pooled.csv, extra_ff_median.csv, extra_corr_person.csv, extra_corr_pooled.csv,
         extra_coverage.csv
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from HackYeah2026.analysiscontext.analysis.common import CACHE
from HackYeah2026.analysiscontext.analysis.corr_target import bh, spearman_eff

warnings.filterwarnings("ignore")
pd.set_option("display.width", 250)
KEEP = ["p01", "p04", "p05", "p06", "p07", "p08", "p09", "p10", "p11", "p14", "p15", "p16"]
OLD = ["sleep_h", "time_in_bed_h", "bedtime_h", "sleep_eff", "rhr_night", "steps", "lightly", "mvpa", "very",
       "srpe_load", "ex_min_nonwalk", "sedentary"]
NEW_NIGHT = ["deep_min", "rem_min", "light_min", "deep_pct", "rem_pct", "wake_min", "wake_pct", "wake_count", "wake_long_n",
             "wake_per_h", "min_after_wake", "ss_overall", "ss_composition", "ss_revitalization", "ss_duration",
             "ss_deep", "ss_restless", "hr_sleep_mean", "hr_sleep_p5"]
NEW_DAY = ["z_fatburn", "z_cardio", "z_peak", "z_cardio_peak", "ex_user_min", "ex_avg_hr", "ex_cp_min",
           "hr_day_mean", "hr_day_p10"]
NEW = NEW_NIGHT + NEW_DAY
MIN_N = 30


def load():
    d = pd.read_csv(CACHE / "analysis_table.csv", parse_dates=["date"])
    x = pd.read_csv(CACHE / "extra_features.csv", parse_dates=["date"]).drop(columns=["ts_local",
                                                                                      "sleep_after_survey"])
    d = d.merge(x, on=["pid", "date"], how="left")
    # derived: nocturnal dip = 1 - night HR / day HR (day D-1, night ending D)
    for v in ("lag1", "avg3"):
        d[f"hr_dip_{v}"] = 1 - d[f"hr_sleep_mean_{v}"] / d[f"hr_day_mean_{v}"]
    return d[d.pid.isin(KEEP)].sort_values(["pid", "date"]).reset_index(drop=True)


def md(df, f=".2f"):
    print(df.to_markdown(floatfmt=f))
    print()


def zpool_spearman(d, cols):
    Z = d.groupby("pid")[cols].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    return Z.corr("spearman", min_periods=200)


def median_spearman(d, cols):
    per = [g[cols].corr("spearman", min_periods=MIN_N).stack(future_stack=True).rename(p) for p, g in d.groupby("pid")]
    return pd.concat(per, axis=1).median(axis=1).unstack().loc[cols, cols]


def main():
    d = load()
    feats_new = NEW + ["hr_dip"]
    # ------------------------------------------------ A quality
    print("# A. Jakość i pokrycie\n")
    print("## A1. Typ snu (wybrane noce główne, noc kończąca się w D, dni z ważnym sleep_h_lag1)\n")
    base = d[d.sleep_h_lag1.notna()]
    t = base.groupby("pid").agg(nights=("sleep_h_lag1", "size"),
                                classic=("sleep_type_lag1", lambda s: (s == "classic").sum()))
    t["classic_pct"] = 100 * t.classic / t.nights
    t.loc["ALL"] = [t.nights.sum(), t.classic.sum(), 100 * t.classic.sum() / t.nights.sum()]
    md(t, ".1f")
    print("## A2. Pokrycie lag1 (% dni ankiety z etykietą)\n")
    cov = d.groupby("pid")[[f"{c}_lag1" for c in ["sleep_h", "steps"] + feats_new]].apply(
        lambda g: 100 * g.notna().mean())
    cov.columns = [c[:-5] for c in cov.columns]
    cov.insert(0, "n_days", d.groupby("pid").size())
    cov.to_csv(CACHE / "extra_coverage.csv")
    md(cov.T, ".0f")
    print("## A3. Zakresy (lag1, dni z etykietą, 12 osób)\n")
    rows = []
    for c in feats_new:
        x = d[f"{c}_lag1"].dropna()
        pp = x.groupby(d.pid).apply(lambda s: s.quantile(.9) - s.quantile(.1))
        rows.append(dict(feature=c, n=len(x), zero_pct=100 * (x == 0).mean(), p1=x.quantile(.01),
                         p10=x.quantile(.1), p50=x.median(), p90=x.quantile(.9), p99=x.quantile(.99),
                         within_p10_p90_med=pp.median(), n_unique_med=x.groupby(d.pid).nunique().median()))
    md(pd.DataFrame(rows).set_index("feature"), ".2f")
    # raw-night checks (all selected nights, not only survey days)
    n = pd.read_csv(CACHE / "extra_night.csv")
    n = n[n.pid.isin(KEEP)]
    st = n[n.sleep_type == "stages"]
    print("## A4. Kontrole wiarygodności (wszystkie wybrane noce, 12 osób)\n")
    print(f"- noce stages: {len(st)}, classic: {(n.sleep_type == 'classic').sum()}")
    print(f"- deep = 0: {(st.deep_min == 0).sum()}, rem = 0: {(st.rem_min == 0).sum()}, "
          f"deep% > 30: {(st.deep_pct > 30).sum()}, rem% > 40: {(st.rem_pct > 40).sum()}")
    print(f"- ss_deep == deep_min: {(st.ss_deep == st.deep_min).mean():.3f} (z nocy z ss)")
    print(f"- ss_overall == composition+revitalization+duration: "
          f"{(n.ss_overall == n.ss_composition + n.ss_revitalization + n.ss_duration).mean():.3f}")
    print(f"- sleep_score brak (wybrane noce): {n.ss_overall.isna().mean():.3f}; ss_overall==0: {(n.ss_overall == 0).sum()}")
    print(f"- min_to_fall > 0: {(n.min_to_fall > 0).sum()} / {len(n)}; min_after_wake > 0: {(n.min_after_wake > 0).mean():.2f}")
    print(f"- awake_in_bed == wake_min + to_fall + after_wake: "
          f"{(n.awake_in_bed == n.wake_min + n.min_to_fall + n.min_after_wake).mean():.3f}")
    print(f"- hr_cover < 0.5: {(n.hr_cover < 0.5).sum()}, hr_sleep_p5 < 35: {(n.hr_sleep_p5 < 35).sum()}, "
          f"hr_sleep_mean > 90: {(n.hr_sleep_mean > 90).sum()}")
    cl = n[n.sleep_type == "classic"]
    print(f"- classic noce: minutesAsleep mediana {cl.minutesAsleep.median()}, wake_min mediana {cl.wake_min.median()} "
          f"vs stages {st.wake_min.median()}; classic restless {cl.classic_restless_min.median()} awake {cl.classic_awake_min.median()}")
    print()
    dy = pd.read_csv(CACHE / "extra_day.csv")
    dy = dy[dy.pid.isin(KEEP) & (dy.wear_day >= 720)]
    print(f"- strefy HR: z_total − wear_min mediana {(dy.z_total - dy.wear_min).median():.0f} min "
          f"(p5 {(dy.z_total - dy.wear_min).quantile(.05):.0f}, p95 {(dy.z_total - dy.wear_min).quantile(.95):.0f}); "
          f"własne strefy (IN_CUSTOM_ZONE) u: {sorted(dy[dy.z_custom == 1].pid.unique())}")
    print(f"- dni z ex_avg_hr (nie-Walk): {dy.ex_avg_hr.notna().mean():.2f}; ex_user_min>0: {(dy.ex_user_min > 0).mean():.2f}")
    print()

    # ------------------------------------------------ B redundancy
    print("# B. Redundancja (lag1, Spearman w obrębie osoby)\n")
    allf = OLD + feats_new
    cols = [f"{c}_lag1" for c in allf]
    P = zpool_spearman(d, cols)
    M = median_spearman(d, cols)
    P.index = P.columns = allf
    M.index = M.columns = allf
    P.to_csv(CACHE / "extra_ff_pooled.csv")
    M.to_csv(CACHE / "extra_ff_median.csv")
    rows = []
    for c in feats_new:
        s = P[c].drop(c).dropna()
        top = s.abs().sort_values(ascending=False).head(4).index
        rows.append(dict(feature=c, **{f"top{i + 1}": f"{k} {P.loc[c, k]:+.2f} ({M.loc[c, k]:+.2f})"
                                       for i, k in enumerate(top)}))
    md(pd.DataFrame(rows).set_index("feature"))
    print("## B2. Nowe vs stare (pooled, w nawiasie mediana per osoba)\n")
    sub = P.loc[feats_new, OLD].round(2).astype(str) + " (" + M.loc[feats_new, OLD].round(2).astype(str) + ")"
    md(sub)

    # ------------------------------------------------ C lag1 vs avg3
    print("# C. lag1 vs avg3 (pooled w obrębie osoby, mediana per osoba)\n")
    rows = []
    for c in feats_new:
        a, b = f"{c}_lag1", f"{c}_avg3"
        p = zpool_spearman(d, [a, b]).iloc[0, 1]
        m = np.nanmedian([g[[a, b]].corr("spearman").iloc[0, 1] for _, g in d.groupby("pid")])
        rows.append(dict(feature=c, rho_pooled=p, rho_median=m))
    md(pd.DataFrame(rows).set_index("feature"))

    # ------------------------------------------------ D feature -> target (information only)
    print("# D. Cecha → cel (TYLKO INFORMACYJNIE)\n")
    fam = OLD + feats_new
    cols = [f"{f}_{v}" for f in fam for v in ("lag1", "avg3")]
    rows = []
    for pid, g in d.groupby("pid"):
        for target in ["comp", "mood"]:
            y = g[target].to_numpy(float)
            for c in cols:
                rho, nn, p, peff, neff = spearman_eff(g[c].to_numpy(float), y)
                if nn < MIN_N or np.isnan(rho):
                    continue
                rows.append(dict(pid=pid, target=target, feature=c, rho=rho, n=nn, p_eff=peff, n_eff=neff))
    R = pd.DataFrame(rows)
    R["q_bh"] = np.nan
    for _, idx in R.groupby(["pid", "target"]).groups.items():
        R.loc[idx, "q_bh"] = bh(R.loc[idx, "p_eff"])
    R["q_bh_new_only"] = np.nan
    newmask = R.feature.str.rsplit("_", n=1).str[0].isin(feats_new)
    for _, idx in R[newmask].groupby(["pid", "target"]).groups.items():
        R.loc[idx, "q_bh_new_only"] = bh(R.loc[idx, "p_eff"])
    R.to_csv(CACHE / "extra_corr_person.csv", index=False)
    print(f"Rodzina BH na osobę i cel: {R.groupby(['pid', 'target']).size().median():.0f} testów "
          f"(runda 1: ok. 27).\n")
    pooled = []
    for target in ["comp", "mood"]:
        for c in cols:
            sub = d[["pid", c, target]].dropna()
            sub = sub[sub.groupby("pid")[c].transform("size") >= MIN_N]
            zz = sub.groupby("pid")[[c, target]].transform(lambda s: (s - s.mean()) / s.std(ddof=0)).dropna()
            rho, p = stats.spearmanr(zz[c], zz[target]) if len(zz) > 30 else (np.nan, np.nan)
            pr = R[(R.target == target) & (R.feature == c)]
            tt = stats.ttest_1samp(pr.rho.dropna(), 0) if len(pr) > 2 else None
            pooled.append(dict(target=target, feature=c, rho_pooled=rho, n=len(zz), persons=len(pr),
                               mean_rho=pr.rho.mean(), n_pos=int((pr.rho > 0).sum()),
                               n_sig=int((pr.p_eff < .05).sum()), n_q10=int((pr.q_bh < .10).sum()),
                               p_between=tt.pvalue if tt else np.nan))
    PP = pd.DataFrame(pooled)
    PP.to_csv(CACHE / "extra_corr_pooled.csv", index=False)
    for target in ["comp", "mood"]:
        print(f"## D1. Dane łączne, cel = {target}\n")
        md(PP[PP.target == target].drop(columns="target").set_index("feature"), ".3f")
    print("## D2. Nowe cechy z q_BH < 0,10 (pełna rodzina stare+nowe) lub p_eff < 0,01, cel comp\n")
    s = R[newmask & (R.target == "comp") & ((R.q_bh < .10) | (R.p_eff < .01))]
    md(s.sort_values(["pid", "p_eff"]).set_index("pid"), ".3f")
    return d, P, M, R, PP


if __name__ == "__main__":
    main()
