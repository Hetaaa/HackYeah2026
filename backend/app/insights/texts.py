"""All English UI texts, generated from templates (no LLM). Short by design: "Under 7h sleep"."""

from app.insights import config as C


def hours(v: float) -> str:
    h, m = divmod(round(v * 60), 60)
    if h == 0:
        return f"{m} min"
    return f"{h}h" if m == 0 else f"{h}h{m:02d}"


def clock(v: float) -> str:
    """bedtime_h = hours since 18:00 of the previous evening."""
    t = round((18 + v) * 60) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def kilo(v: float) -> str:
    """Compact count for texts: 950, 4k, 7.8k."""
    if abs(v) < 1000:
        return f"{v:.0f}"
    return f"{round(v / 1000, 1):g}k"


def fmt(name: str, v: float) -> str:
    """Display value of a feature (day view, timeline, charts)."""
    unit = C.FEATURES[name].unit
    if unit == "h":
        return hours(v)
    if unit == "clock":
        return clock(v)
    if unit == "%":
        # 12.4 % must not print as "12%" next to a pattern threshold of 12 %
        return f"{v:.0f}%" if float(v).is_integer() else f"{v:.1f}%"
    if unit == "bpm":
        return f"{v:.0f} bpm"
    if unit == "steps":
        return f"{v:,.0f}"
    if unit == "pts":
        return f"{v:.0f}"
    return f"{v:.0f} min"


def amount(name: str, v: float) -> str:
    """Value inside a text: like fmt, but compact (4k steps, 5h20 instead of 320 min)."""
    unit = C.FEATURES[name].unit
    if unit == "steps":
        return kilo(v)
    if unit == "min" and abs(v) >= 60:
        return hours(v / 60)
    return fmt(name, v)


CONDITION = {
    "sleep_h": ("Under {v} sleep", "Over {v} sleep"),
    "bedtime_h": ("Asleep before {v}", "Asleep after {v}"),
    "wake_pct": ("Awake under {v} of night", "Awake over {v} of night"),
    "rem_pct": ("REM under {v}", "REM over {v}"),
    "hr_sleep_mean": ("Sleep HR under {v}", "Sleep HR over {v}"),
    "steps": ("Under {v} steps", "Over {v} steps"),
    "mvpa": ("Under {v} brisk activity", "Over {v} brisk activity"),
    "z_cardio_peak": ("Under {v} hard exercise", "Over {v} hard exercise"),
    "lightly": ("Under {v} light activity", "Over {v} light activity"),
}
VALUE = {
    "sleep_h": "{v} sleep",
    "bedtime_h": "asleep at {v}",
    "wake_pct": "awake {v} of night",
    "rem_pct": "REM {v}",
    "hr_sleep_mean": "sleep HR {v}",
    "steps": "{v} steps",
    "mvpa": "{v} brisk activity",
    "z_cardio_peak": "{v} hard exercise",
    "lightly": "{v} light activity",
}
SIGNAL_LEAD = {"bad": "Heads-up", "good": "Good sign"}


def window(name: str, variant: str) -> str:
    night = C.FEATURES[name].night
    if variant == "avg3":
        return " (3-night avg)" if night else " (3-day avg)"
    return "" if night else " (day before)"


def pattern_condition(p: dict) -> str:
    """Short condition of a pattern: "Under 6h sleep", "Under 4k steps (day before)"."""
    phrase = CONDITION[p["feature"]][p["op"] == "above"]
    return phrase.format(v=amount(p["feature"], p["threshold"])) + window(
        p["feature"], p["variant"]
    )


def pattern_text(p: dict) -> str:
    return (
        f"{pattern_condition(p)}: {p['target_days_in_condition']} of "
        f"{p['days_in_condition']} days {p['kind']}"
    )


def value_text(name: str, variant: str, x: float) -> str:
    return VALUE[name].format(v=amount(name, x)) + window(name, variant)


def reason_text(name: str, variant: str, x: float) -> str:
    return f"Possible reason: {value_text(name, variant, x)}"


def signal_text(kind: str, value: str) -> str:
    return f"{SIGNAL_LEAD[kind]}: {value}"


NO_REASON = "No clear reason"

# survey items that move with a pattern (worse on bad-day patterns, better on good-day ones)
DRIVER = {
    "mood": {"bad": "lower mood", "good": "better mood"},
    "fatigue": {"bad": "more tired", "good": "more rested"},
    "stress": {"bad": "more stressed", "good": "less stressed"},
}


def driver_text(item: str, kind: str) -> str:
    return DRIVER[item][kind]


def drivers_text(drivers: list[dict]) -> str | None:
    """What changes on those days: "Mostly: more tired, more stressed"."""
    if not drivers:
        return None
    return "Mostly: " + ", ".join(d["text"] for d in drivers)


COMPARE_LABEL = {
    "sleep_h": "Sleep",
    "bedtime_h": "Bedtime",
    "wake_pct": "Awake at night",
    "rem_pct": "REM",
    "hr_sleep_mean": "Sleep HR",
    "steps": "Steps (day before)",
    "mvpa": "Brisk activity (day before)",
    "z_cardio_peak": "Hard exercise (day before)",
    "lightly": "Light activity (day before)",
}
COMPARE_REF = {"good_days": "vs good days", "all_days": "vs usual"}


def compare_ref(norm_source: str) -> str:
    return COMPARE_REF[norm_source]


def signed(name: str, d: float) -> str:
    """Signed difference in the feature's unit: "-1h43", "+15 bpm", "+3%"."""
    a = abs(d)
    unit = C.FEATURES[name].unit
    if unit in ("h", "clock"):
        size = hours(a)
    elif unit == "%":
        size = f"{a:.0f}%"
    else:
        size = amount(name, a)
    return f"{'+' if d > 0 else '-'}{size}"


def compare_text(name: str, d: float, ref: str) -> str:
    """Signed difference from the reference day: "Sleep -1h43 vs good days"."""
    return f"{COMPARE_LABEL[name]} {signed(name, d)} {ref}"


OUTLOOK = {
    "tough": "Tougher day possible",
    "promising": "Looks like a good day",
    "mixed": "Mixed signals today",
    "neutral": "Nothing stands out today",
    "unknown": "No watch data yet",
}
CHECKIN_SAVED = "Typical day for you"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def status_summary(status: str, kind: str, n: int, have: int, needed: int) -> str:
    """Headline of the patterns (kind "bad") or recipe (kind "good") screen."""
    common = {
        "insufficient_days": f"Keep checking in: {have}/{needed} days",
        "insufficient_variation": "Check-ins too similar to compare",
    }
    if status in common:
        return common[status]
    if status == "preliminary":  # shown like significant patterns (level tells them apart)
        status = "ok"
    if kind == "bad":
        return {
            "ok": f"{_plural(n, 'possible reason')} for bad days",
            "not_enough_evidence": "No clear pattern yet",
            "insufficient_bad_days": "Not enough bad days yet",
        }[status]
    return {
        "ok": f"{_plural(n, 'thing')} your good days share",
        "not_enough_evidence": "No clear recipe yet",
        "insufficient_good_days": "Not enough good days yet",
    }[status]


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
