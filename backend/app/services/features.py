from app.insights import config as C
from app.schemas import FeatureRead

# UI copy (kept out of app/insights/config.py, which holds the frozen algorithm parameters)
GROUPS = {
    "A": "Sleep length",
    "B": "Bedtime",
    "C": "Sleep continuity",
    "D": "Movement",
    "E": "Exercise",
    "F": "Light activity",
    "G": "Sleep stages",
    "I": "Night heart rate",
}
DESCRIPTIONS = {
    "sleep_h": "Time asleep during the main sleep that ended this morning.",
    "bedtime_h": "When you fell asleep (hours after 18:00 the evening before).",
    "wake_pct": "Share of time in bed spent awake during the night.",
    "steps": "Steps during the day.",
    "z_cardio_peak": "Minutes in the cardio and peak heart-rate zones (hard exercise).",
    "mvpa": "Minutes of moderate and vigorous activity.",
    "lightly": "Minutes of light activity such as walking around or chores.",
    "rem_pct": "Share of sleep spent in REM, the dream stage.",
    "hr_sleep_mean": "Average heart rate while asleep; higher than usual can mean strain.",
    "sleep_eff": "The watch's sleep efficiency score (shown for context only).",
    "rhr_night": "Resting heart rate measured overnight (shown for context only).",
    "time_in_bed_h": "Time from lying down to getting up (shown for context only).",
    "sedentary": "Minutes spent sitting or lying while awake (shown for context only).",
    "wake_min": "Minutes awake during the night (shown for context only).",
    "deep_pct": "Share of sleep in deep sleep (shown for context only).",
    "ss_overall": "The watch's overall sleep score (shown for context only).",
}


def list_features() -> list[FeatureRead]:
    return [
        FeatureRead(
            feature=name,
            label=f.label,
            unit=f.unit,
            group=f.group,
            group_label=GROUPS[f.group],
            when="last_night" if f.night else "day_before",
            tested_direction="lower" if f.bad_when == "below" else "higher",
            can_be_pattern=f.mode == "search",
            description=DESCRIPTIONS[name],
        )
        for name, f in C.FEATURES.items()
    ]
