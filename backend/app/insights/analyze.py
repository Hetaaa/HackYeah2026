"""Entry point of the algorithm: one user's normalized data -> everything the UI shows."""

import pandas as pd

from app.insights import calendar, cleaning, engine, texts
from app.insights import config as C
from app.insights.user import UserData


def _num(v: object) -> float | None:
    return None if pd.isna(v) else round(float(v), 3)


def analyze_user(
    user: UserData, window_end: pd.Timestamp | None = None, all_dates: bool = False
) -> dict:
    """Patterns + per-day content for one user. Deterministic, ~0.1 s for 150 days.

    window_end: days on/after it get calendar content but are not used to find patterns
    (PMData demo: config.PMDATA_WINDOW_END; real users: None).
    all_dates: a day entry for every date with any data, not only days with a check-in.
    Returns {"info": gates and counts, "patterns": {"bad", "good"}, "stats": good vs bad day
    averages per feature, "days": [...]}.
    """
    table, info = cleaning.build_table(user, window_end, all_dates)
    patterns = engine.find_patterns(table, info)
    for kind in patterns.values():
        for p in kind["patterns"]:
            p["text"] = texts.pattern_text(p)

    table = table.sort_values("date")
    window = table[table.in_analysis_window]
    nrm, source = calendar.norms(window)
    stats = calendar.label_stats(window)
    info["norm_source"] = source
    ref = texts.compare_ref(source)
    feats = list(engine.search_features(info["group_e_feature"]))
    raw = _raw_values(user, feats)
    info["first_date"] = str(table.date.min().date()) if len(table) else None
    info["last_date"] = str(table.date.max().date()) if len(table) else None
    info["n_window_days"] = len(window)
    info["window_first_date"] = str(window.date.min().date()) if len(window) else None
    info["window_last_date"] = str(window.date.max().date()) if len(window) else None

    days = []
    for _, row in table.iterrows():
        label = row.label if isinstance(row.label, str) else None
        signals = {k: calendar.day_reasons(row, patterns[k]["patterns"], nrm) for k in patterns}
        reasons = signals[label] if label in ("bad", "good") else []
        days.append(
            {
                "date": str(row.date.date()),
                "label": label,
                "score": _num(row.z),
                "outside_window": bool(row.outside_window),
                "survey": {f: _num(row[f]) for f in C.SURVEY_RAW},
                "reasons": reasons,
                "signals": signals,
                "no_reason_text": texts.NO_REASON
                if label in ("bad", "good") and not reasons
                else None,
                "compare": calendar.compare_day(row, nrm, feats, ref, stats),
                "values": calendar.values(row, nrm, stats),
                "raw": raw.get(row.date, {"night": {}, "activity": {}}),
                "late_night": bool(row.sleep_after_survey),
            }
        )
    return {"info": info, "patterns": patterns, "stats": stats, "days": days}


def _raw_values(user: UserData, feats: list[str]) -> dict:
    """Per date: the night that ended that morning and that calendar day's activity (search
    features only, worn-day filter applied) - the building blocks of the day-view timeline."""
    nights = user.nights
    days = cleaning.activity(user.days)
    out: dict = {}
    for name in feats:
        f = C.FEATURES[name]
        series = nights[name] if f.night else days[name]
        for date, value in pd.to_numeric(series, errors="coerce").dropna().items():
            part = "night" if f.night else "activity"
            out.setdefault(date, {"night": {}, "activity": {}})[part][name] = round(float(value), 3)
    return out
