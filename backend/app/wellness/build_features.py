import argparse
from pathlib import Path

import numpy as np
import pandas as pd

LABELS = {"bad": 0, "neutral": 1, "good": 2}
WATCH = [
    "sleep_h_lag1",
    "sleep_h_avg3",
    "time_in_bed_h_lag1",
    "ss_overall_lag1",
    "sleep_eff_lag1",
    "deep_pct_lag1",
    "rem_pct_lag1",
    "rhr_night_lag1",
    "hr_sleep_mean_lag1",
    "steps_lag1",
    "mvpa_lag1",
    "mvpa_avg3",
    "sedentary_lag1",
    "weekday",
    "weekend_Dm1",
]
SURVEY = ["mood", "fatigue", "stress", "sleep_quality", "comp", "label"]
RELATIVE = [
    "sleep_vs_norm",
    "sleep_debt_3n",
    "short_sleep_after_hard_day",
    "comp_base",
    "bad_share_past",
    "good_share_past",
]
FEATURES = WATCH + [f"{c}_y" for c in SURVEY] + ["comp_avg3_past"] + RELATIVE
SLEEP = [
    c
    for c in WATCH
    if c not in {"steps_lag1", "mvpa_lag1", "mvpa_avg3", "sedentary_lag1", "weekday", "weekend_Dm1"}
]


def truth(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "1.0"])


def build_features(
    raw: pd.DataFrame, safeguard: bool = True, keep_unlabeled: bool = False
) -> pd.DataFrame:
    df = raw.copy()
    df["date"] = pd.to_datetime(df.date).dt.normalize()
    if df.duplicated(["pid", "date"]).any():
        raise ValueError("Duplicate user-day rows")
    unknown = df.label.notna() & ~df.label.isin([*LABELS, 0, 1, 2])
    if unknown.any():
        raise ValueError("Unknown label")
    df["label"] = df.label.map(LABELS).where(
        df.label.isin(LABELS), pd.to_numeric(df.label, errors="coerce")
    )
    if (df.label.notna() & ~df.label.isin([0, 1, 2])).any():
        raise ValueError("Unknown label")
    eligible = truth(df.in_analysis_window)
    df = df[eligible & (df.label.notna() | keep_unlabeled)].sort_values(["pid", "date"])
    df = df.reset_index(drop=True)
    for c in WATCH + SURVEY:
        if c not in df:
            df[c] = np.nan
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if safeguard and "sleep_after_survey" in df:
        df.loc[truth(df.sleep_after_survey), SLEEP] = np.nan
    parts = []
    for _, g in df.groupby("pid", sort=False):
        g = g.copy()
        consecutive = g.date.diff().eq(pd.Timedelta(days=1))
        for c in SURVEY:
            g[f"{c}_y"] = g[c].shift(1).where(consecutive)
        past_comp = g.comp.shift(1)
        g["comp_avg3_past"] = past_comp.rolling(3, min_periods=2).mean()
        norm = g.sleep_h_lag1.shift(1).rolling(28, min_periods=7).mean()
        g["sleep_vs_norm"] = g.sleep_h_lag1 - norm
        g["sleep_debt_3n"] = 3 * norm - g.sleep_h_lag1.rolling(3, min_periods=3).sum()
        mvpa_norm = g.mvpa_lag1.shift(1).rolling(7, min_periods=4).mean()
        g["short_sleep_after_hard_day"] = (
            ((g.sleep_vs_norm < -0.75) & (g.mvpa_lag1 > mvpa_norm))
            .astype(float)
            .where(g.sleep_vs_norm.notna())
        )
        g["comp_base"] = past_comp.expanding(min_periods=5).mean()
        for label, name in [(0, "bad"), (2, "good")]:
            g[f"{name}_share_past"] = (
                g.label.eq(label)
                .astype(float)
                .where(g.label.notna())
                .shift(1)
                .expanding(min_periods=5)
                .mean()
            )
        # Mask derived sleep values too: no unavailable sleep enters the prediction.
        if safeguard and "sleep_after_survey" in g:
            g.loc[truth(g.sleep_after_survey), RELATIVE[:3]] = np.nan
        parts.append(g[["pid", "date", "label", *FEATURES]])
    return (
        pd.concat(parts, ignore_index=True)
        if parts
        else pd.DataFrame(columns=["pid", "date", "label", *FEATURES])
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("features.csv"))
    args = parser.parse_args()
    build_features(pd.read_csv(args.input)).to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
