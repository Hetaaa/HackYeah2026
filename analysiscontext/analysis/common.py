"""Shared helpers: loading daily table, label definitions, feature lists."""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
LOCKDOWN = pd.Timestamp("2020-03-12")
LABEL_FIELDS = ["mood", "fatigue", "stress"]

# candidate features: (column base, expected direction for GOOD day: +1 higher better, -1 lower better)
FEATURES = {
    "sleep_h": +1, "sleep_eff": +1, "bedtime_h": -1, "time_in_bed_h": +1,
    "rhr_night": -1, "rhr_day": -1,
    "steps": +1, "lightly": +1, "mvpa": +1, "very": +1, "active_total": +1, "sedentary": -1,
    "distance_km": +1, "calories": +1,
    "srpe_load": 0, "ex_min": 0,
}
CORE = ["sleep_h", "sleep_eff", "bedtime_h", "rhr_night", "rhr_day", "steps", "lightly", "mvpa", "sedentary",
        "srpe_load"]


def load_daily():
    d = pd.read_csv(CACHE / "daily.csv", parse_dates=["ts_local", "date"])
    return d


def _z(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and sd > 0 else s * np.nan


def label_spec(df, fields=LABEL_FIELDS):
    """As in koncepcja-analityczna 1.5: z per field (mean/SD), mean, z again."""
    zz = df.groupby("pid")[fields].transform(_z)
    comp = zz.mean(axis=1, skipna=True)
    comp[df[fields].notna().sum(axis=1) < len(fields)] = np.nan
    return comp.groupby(df.pid).transform(_z)


def label_median(df, fields=LABEL_FIELDS):
    """Median-centred variant: (x - median_person)/SD_person per field, mean, divide by SD (no re-centring).
    Person's typical day (all fields at their median) -> 0 -> neutral."""
    def dev(s):
        sd = s.std(ddof=0)
        return (s - s.median()) / sd if sd and sd > 0 else s * 0.0
    zz = df.groupby("pid")[fields].transform(dev)
    comp = zz.mean(axis=1, skipna=True)
    comp[df[fields].notna().sum(axis=1) < len(fields)] = np.nan
    sd = comp.groupby(df.pid).transform(lambda s: s.std(ddof=0))
    return comp / sd.replace(0, np.nan)


def to_label(z, thr=0.5):
    return pd.Series(np.select([z < -thr, z > thr], ["bad", "good"], "neutral"), index=z.index).where(z.notna())
