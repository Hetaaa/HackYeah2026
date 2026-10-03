"""Per-person correlation matrix + top associations with confounder checks (reads cache/corr_person.csv)."""
import pandas as pd, numpy as np
from HackYeah2026.analysiscontext.analysis.common import CACHE
R = pd.read_csv(CACHE / "corr_person.csv")
KEY = ["sleep_h_lag1", "sleep_h_avg3", "sleep_eff_lag1", "bedtime_h_lag1", "rhr_night_lag1", "rhr_night_avg3",
       "steps_lag1", "steps_avg3", "lightly_lag1", "lightly_avg3", "mvpa_lag1", "mvpa_avg3", "sedentary_lag1", "srpe_load_lag1"]
def cell(r):
    s = f"{r.rho:+.2f}"
    if r.q_bh < .10: s += "**"
    elif r.p_eff < .05: s += "*"
    return s
for target in ["comp", "mood"]:
    sub = R[(R.target == target) & R.feature.isin(KEY)].copy()
    sub["cell"] = sub.apply(cell, axis=1)
    M = sub.pivot(index="pid", columns="feature", values="cell")[KEY]
    n = sub.groupby("pid").n.max()
    M.insert(0, "n_max", n)
    print(f"## per-person rho, target={target}  (* p_eff<.05, ** BH q<.10 within person)")
    print(M.fillna("").to_markdown())
    print()
print("## top-3 associations per person (composite), |rho| ranked, with robustness")
T = R[(R.target == "comp") & ~R.feature.str.contains("dev28|time_in_bed|ex_min|rhr_day")]
top = T.assign(a=T.rho.abs()).sort_values("a", ascending=False).groupby("pid").head(3).sort_values(["pid", "a"], ascending=[True, False])
print(top[["pid", "feature", "rho", "n", "p_eff", "n_eff", "q_bh", "rho_weekday", "n_weekday", "rho_prelock", "rho_partial"]].to_markdown(index=False, floatfmt=".2f"))
print("\nper-person significant (q<.10) composite associations:")
print(R[(R.target=="comp")&(R.q_bh<.10)][["pid","feature","rho","n","p_eff","q_bh","rho_weekday","rho_prelock","rho_partial"]].to_markdown(index=False,floatfmt=".3f"))
print("\nper-person significant (q<.10) mood associations:")
print(R[(R.target=="mood")&(R.q_bh<.10)][["pid","feature","rho","n","p_eff","q_bh","rho_weekday","rho_prelock","rho_partial"]].to_markdown(index=False,floatfmt=".3f"))
