"""Entry point of the algorithm: one user's normalized data -> everything the UI shows."""

import pandas as pd

from app.insights import calendar, cleaning, engine, texts
from app.insights import config as C
from app.insights.user import UserData


def _num(v: object) -> float | None:
    return None if pd.isna(v) else round(float(v), 3)


def analyze_user(user: UserData, window_end: pd.Timestamp | None = None) -> dict:
    """Patterns + per-day content for one user. Deterministic, ~0.1 s for 150 days.

    window_end: days on/after it get calendar content but are not used to find patterns
    (PMData demo: config.PMDATA_WINDOW_END; real users: None).
    Returns {"info": gates and counts, "patterns": {"bad", "good"}, "days": [...]}.
    """
    table, info = cleaning.build_table(user, window_end)
    patterns = engine.find_patterns(table, info)
    for kind in patterns.values():
        for p in kind["patterns"]:
            p["text"] = texts.pattern_text(p)

    table = table.sort_values("date")
    nrm, source = calendar.norms(table[table.in_analysis_window])
    info["norm_source"] = source
    ref = "on your average good day" if source == "good_days" else "on your average day"
    feats = list(engine.search_features(info["group_e_feature"]))
    info["first_date"] = str(table.date.min().date()) if len(table) else None
    info["last_date"] = str(table.date.max().date()) if len(table) else None

    days = []
    for _, row in table.iterrows():
        label = row.label if isinstance(row.label, str) else None
        reasons = []
        if label in ("bad", "good"):
            reasons = calendar.day_reasons(row, patterns[label]["patterns"], nrm)
        days.append(
            {
                "date": str(row.date.date()),
                "label": label,
                "score": _num(row.z),
                "outside_window": bool(row.outside_window),
                "survey": {f: _num(row[f]) for f in C.SURVEY_RAW},
                "reasons": reasons,
                "no_reason_text": texts.NO_REASON
                if label in ("bad", "good") and not reasons
                else None,
                "compare": calendar.compare_day(row, nrm, feats, ref),
                "values": calendar.values(row, nrm),
            }
        )
    return {"info": info, "patterns": patterns, "days": days}
