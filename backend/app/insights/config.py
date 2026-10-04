"""Frozen parameters of the insights pipeline (see docs/insights.md for the reasoning).

Everything here was fixed before looking at final pattern results and validated on shuffled labels.
Changing a value means re-running the validation in analysis/validate.py (outside this repo).
"""

from dataclasses import dataclass

import pandas as pd

TZ = "Europe/Oslo"
# PMData demo only: patterns are searched on days before the Norwegian COVID lockdown
PMDATA_WINDOW_END = pd.Timestamp("2020-03-12")

# ---- survey + label
LABEL_FIELDS = ["mood", "fatigue", "stress"]
SURVEY_RAW = [
    "mood",
    "fatigue",
    "stress",
    "readiness",
    "soreness",
    "sleep_quality",
    "sleep_duration_h",
]
SCALE15 = ["fatigue", "mood", "sleep_quality", "soreness", "stress"]
NIGHT_REPORT_END_H = 5  # reports before 05:00 local belong to the previous day
DEAD_ZONE = 0.5  # |z| <= 0.5 -> neutral
MIN_LABEL_DAYS = 14  # fewer check-ins: absolute label (no personal baseline yet)

# ---- cleaning
WEAR_DAY_MIN = 720  # minutes worn between 06:00 and 24:00, otherwise activity of that day is NaN
SED_WEAR_MIN = 1200  # sedentary minutes trusted only with >= 20 h total wear
MIN_SLEEP_MIN = 120  # main sleep shorter than 2 h = artefact
SLEEP_END_TOL_MIN = 60  # sleep must end <= survey time + 60 min to be "before the survey"
NIGHT_HR_MIN_COVER = 0.5  # >= 50 % of sleep minutes need a heart-rate reading
VALID = {  # value outside the range -> NaN
    "sleep_h": (2, 14),
    "wake_pct": (0, 50),
    "rem_pct": (0, 50),
    "hr_sleep_mean": (35, 110),
    "rhr_night": (30, 110),
    "steps": (0, 60000),
}

# ---- participant gates
MIN_RAW_SD = 0.20
MIN_FULL_DAYS = 60
MIN_BAD_DAYS = 15
MIN_GOOD_DAYS = 15
E_HRZ_MIN_DAYS = 20  # group E uses z_cardio_peak if >= 20 days with > 10 min, otherwise mvpa
E_HRZ_MIN_MIN = 10

# ---- pattern engine
MIN_SUPPORT = 10
MAX_COVER = 0.5
ALPHA = 0.05
# display only: lists are filled up to MAX_PATTERNS with "exploratory" patterns (per-feature p
# <= 0.20); they are never a day's reason or a morning signal, so the validation is unaffected
FILL_ALPHA = 0.20
MIN_SHIFT = 14
MAX_PATTERNS = 3

# ---- calendar
MAX_REASONS = 2
MIN_NORM_DAYS = 10
COMPARE_MIN_Z = 1.0
COMPARE_MAX = 2
DRIVER_MIN_DIFF = 0.3  # survey item counts as a driver from 0.3 points (1-5 scale)
STATS_MIN_DAYS = 3  # good/bad day average shown only from 3 days on
LEAN_MIN_DAYS = 5  # "leans" towards good/bad days needs >= 5 good and >= 5 bad days
LEAN_MIN_GAP = 0.2  # ...and good and bad day means >= 0.2 SD apart, otherwise no lean


@dataclass(frozen=True)
class Feature:
    group: str
    variants: tuple[str, ...]
    bad_when: str  # "below" | "above"
    grid_step: float
    mode: str  # "search" (pattern engine) | "view" (day view only)
    label: str
    unit: str
    z_floor: float
    night: bool  # night feature (last night) vs day feature (the day before)

    def columns(self, name: str) -> list[str]:
        return [f"{name}_{v}" for v in self.variants]


FEATURES: dict[str, Feature] = {
    "sleep_h": Feature("A", ("lag1", "avg3"), "below", 0.5, "search", "Sleep", "h", 0.25, True),
    "bedtime_h": Feature(
        "B", ("lag1", "avg3"), "above", 0.5, "search", "Bedtime", "clock", 0.25, True
    ),
    "wake_pct": Feature("C", ("lag1",), "above", 1.0, "search", "Awake at night", "%", 1.0, True),
    "steps": Feature("D", ("lag1", "avg3"), "below", 1000, "search", "Steps", "steps", 500, False),
    "z_cardio_peak": Feature(
        "E", ("lag1", "avg3"), "above", 10, "search", "High heart-rate zones", "min", 5, False
    ),
    "mvpa": Feature(
        "E", ("lag1", "avg3"), "below", 10, "search", "Brisk activity", "min", 5, False
    ),
    "lightly": Feature(
        "F", ("lag1", "avg3"), "below", 20, "search", "Light activity", "min", 10, False
    ),
    "rem_pct": Feature("G", ("lag1",), "below", 2.0, "search", "REM sleep", "%", 1.0, True),
    "hr_sleep_mean": Feature(
        "I", ("lag1",), "above", 1.0, "search", "Heart rate during sleep", "bpm", 1.0, True
    ),
    "sleep_eff": Feature("C", ("lag1",), "below", 1.0, "view", "Sleep efficiency", "%", 1.0, True),
    "rhr_night": Feature(
        "I", ("lag1",), "above", 1.0, "view", "Resting heart rate", "bpm", 1.0, True
    ),
    "time_in_bed_h": Feature("A", ("lag1",), "below", 0.5, "view", "Time in bed", "h", 0.25, True),
    "sedentary": Feature("D", ("lag1",), "above", 30, "view", "Sedentary time", "min", 15, False),
    "wake_min": Feature("C", ("lag1",), "above", 5, "view", "Minutes awake", "min", 3, True),
    "deep_pct": Feature("G", ("lag1",), "below", 2.0, "view", "Deep sleep", "%", 1.0, True),
    "ss_overall": Feature("A", ("lag1",), "below", 5, "view", "Sleep score", "pts", 2, True),
}
NIGHT_COLS = [n for n, f in FEATURES.items() if f.night]
DAY_COLS = [n for n, f in FEATURES.items() if not f.night]


@dataclass(frozen=True)
class Persona:
    role: str  # "main" | "backup"
    name: str
    tagline: str


PERSONAS: dict[str, Persona] = {
    "p06": Persona("main", "Alex", "Sleep length shapes the good days"),
    "p01": Persona("main", "Robin", "Hard training days take their toll"),
    "p10": Persona("main", "Sam", "Restless nights, light movement"),
    "p16": Persona("backup", "Kim", "A night owl whose sleep sets the tone"),
}
