"""English UI texts generated from templates (no LLM)."""

from app.insights import config as C


def hours(v: float) -> str:
    h, m = divmod(round(v * 60), 60)
    if h == 0:
        return f"{m} min"
    return f"{h} h" if m == 0 else f"{h} h {m:02d} min"


def clock(v: float) -> str:
    """bedtime_h = hours since 18:00 of the previous evening."""
    t = round((18 + v) * 60) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def fmt(name: str, v: float) -> str:
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


CONDITION = {  # (below, above) phrases with {v}
    "sleep_h": ("you sleep under {v}", "you sleep over {v}"),
    "bedtime_h": ("you fall asleep before {v}", "you fall asleep after {v}"),
    "wake_pct": ("you are awake under {v} of the night", "you are awake over {v} of the night"),
    "rem_pct": ("your REM sleep is under {v}", "your REM sleep is over {v}"),
    "hr_sleep_mean": (
        "your heart rate during sleep is under {v}",
        "your heart rate during sleep is over {v}",
    ),
    "steps": ("you walk fewer than {v} steps", "you walk more than {v} steps"),
    "mvpa": ("you get under {v} of brisk activity", "you get over {v} of brisk activity"),
    "z_cardio_peak": (
        "you spend under {v} in high heart-rate zones",
        "you spend over {v} in high heart-rate zones",
    ),
    "lightly": ("you get under {v} of light activity", "you get over {v} of light activity"),
}
VALUE = {  # night phrases say "last night"; avg3 swaps it for the 3-night window
    "sleep_h": "you slept {v} last night",
    "bedtime_h": "you fell asleep at {v} last night",
    "wake_pct": "you were awake {v} of last night",
    "rem_pct": "your REM sleep was {v} last night",
    "hr_sleep_mean": "your heart rate during sleep was {v} last night",
    "steps": "you walked {v} steps",
    "mvpa": "you had {v} of brisk activity",
    "z_cardio_peak": "you spent {v} in high heart-rate zones",
    "lightly": "you had {v} of light activity",
}


def window(name: str, variant: str) -> str:
    night = C.FEATURES[name].night
    if variant == "avg3":
        return (
            " on average over the last 3 nights"
            if night
            else " on average over the previous 3 days"
        )
    return "" if night else " the day before"


def value_text(name: str, variant: str, x: float) -> str:
    t = VALUE[name].format(v=fmt(name, x))
    if variant == "avg3":
        t = t.replace(" last night", "")
    return t + window(name, variant)


def pattern_text(p: dict) -> str:
    cond = CONDITION[p["feature"]][p["op"] == "above"].format(v=fmt(p["feature"], p["threshold"]))
    lead = "" if p["level"] == "significant" else "Early signal: "
    return (
        f"{lead}When {cond}{window(p['feature'], p['variant'])}, "
        f"{p['target_days_in_condition']} of {p['days_in_condition']} days were {p['kind']} days "
        f"(vs {p['rate_out']:.0%} otherwise)."
    )


def reason_text(name: str, variant: str, x: float) -> str:
    return f"Possible reason: {value_text(name, variant, x)}."


NO_REASON = "No clear pattern explains this day."


def compare_text(name: str, d: float, ref: str) -> str:
    """Descriptive comparison with the reference day ("on your average good day")."""
    more, a = d > 0, abs(d)
    if name == "sleep_h":
        return f"You slept {hours(a)} {'more' if more else 'less'} than {ref}."
    if name == "bedtime_h":
        return f"You fell asleep {hours(a)} {'later' if more else 'earlier'} than {ref}."
    if name == "wake_pct":
        word = "more" if more else "less"
        return f"You were awake {a:.0f} percentage points {word} of the night than {ref}."
    if name == "rem_pct":
        word = "higher" if more else "lower"
        return f"Your REM sleep was {a:.0f} percentage points {word} than {ref}."
    if name == "hr_sleep_mean":
        word = "higher" if more else "lower"
        return f"Your heart rate during sleep was {a:.0f} bpm {word} than {ref}."
    if name == "steps":
        return f"The day before you walked {a:,.0f} {'more' if more else 'fewer'} steps than {ref}."
    what = {
        "mvpa": "brisk activity",
        "z_cardio_peak": "time in high heart-rate zones",
        "lightly": "light activity",
    }[name]
    return f"The day before you had {a:.0f} min {'more' if more else 'less'} {what} than {ref}."
