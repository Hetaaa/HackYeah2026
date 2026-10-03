"""Wellness analysis for the API: Day rows -> validated insights algorithm -> API schemas.

The algorithm lives in app/insights (cleaning, pattern engine, day texts; see docs/insights.md).
Services call `analyze(days, window_end)` once per request and read everything from the result
with the functions below. One user takes ~0.1 s; results are cached per user and data version,
so the calendar does not recompute per day and a saved survey is picked up immediately.
"""

import datetime as dt
import threading
from collections import OrderedDict
from dataclasses import dataclass

import pandas as pd

from app.insights import config as C
from app.insights import engine, texts
from app.insights.analyze import analyze_user
from app.insights.sources.rows import user_from_rows
from app.models import Day, SurveyBase
from app.schemas import (
    DayDetail,
    DaySummary,
    Deviation,
    FeatureValue,
    Ingredient,
    InsightStatus,
    Label,
    NormRange,
    Pattern,
    PatternReport,
    Reason,
    Recipe,
)


@dataclass(frozen=True)
class FeatureInfo:
    label: str
    unit: str


FEATURES: dict[str, FeatureInfo] = {n: FeatureInfo(f.label, f.unit) for n, f in C.FEATURES.items()}
CACHE_SIZE = 32
_cache: OrderedDict[tuple, dict] = OrderedDict()
_lock = threading.Lock()  # sync routes run in a threadpool: compute each version once


def analyze(days: list[Day], window_end: dt.date | None = None) -> dict:
    """Full analysis of one user's days (all rows of that user, any order)."""
    rows = [day.model_dump(exclude={"id"}) for day in days]
    key = (window_end, tuple(tuple(sorted(row.items(), key=lambda kv: kv[0])) for row in rows))
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            return cached
        user_id = rows[0]["user_id"] if rows else ""
        end = pd.Timestamp(window_end) if window_end else None
        result = analyze_user(user_from_rows(user_id, rows), end, all_dates=True)
        result["by_date"] = {entry["date"]: entry for entry in result["days"]}
        _cache[key] = result
        if len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
        return result


# ---------------------------------------------------------------- user level
def insights_status(analysis: dict) -> InsightStatus:
    info = analysis["info"]
    return "ok" if info["included"] else info["exclusion_reasons"][0]


def days_with_data(analysis: dict) -> tuple[int, int]:
    """(days with a check-in and watch data, days needed before insights appear)."""
    return analysis["info"]["n_full_days"], analysis["info"]["n_full_days_needed"]


def label_mode(analysis: dict) -> str:
    """'personal' (relative to the user's history) or 'absolute' (< 14 check-ins / no spread)."""
    return analysis["info"]["label_source"]


def norm_reference(analysis: dict) -> str:
    """'good_days', or 'all_days' when the user has fewer than 10 good days."""
    return analysis["info"]["norm_source"]


# ---------------------------------------------------------------- day level
def _entry(analysis: dict, date: dt.date) -> dict | None:
    return analysis["by_date"].get(date.isoformat())


def score_day(analysis: dict, date: dt.date) -> float | None:
    entry = _entry(analysis, date)
    return entry["score"] if entry else None


def label_day(analysis: dict, date: dt.date) -> Label | None:
    entry = _entry(analysis, date)
    return entry["label"] if entry else None


def _norm(norm: dict | None, average: float | None) -> NormRange | None:
    return NormRange(**norm, average=average) if norm else None


def _deviation(c: dict) -> Deviation:
    info = FEATURES[c["feature"]]
    return Deviation(
        feature=c["feature"],
        label=info.label,
        unit=info.unit,
        value=c["value"],
        norm=_norm(c["norm"], c["reference"]),
        difference=c["diff"],
        z=c["z"],
        direction="higher" if c["diff"] > 0 else "lower",
        text=c["text"],
    )


def _reason(r: dict) -> Reason:
    return Reason(
        feature=r["feature"],
        label=FEATURES[r["feature"]].label,
        value=r["value"],
        display=texts.fmt(r["feature"], r["value"]),
        text=r["text"],
        pattern_text=r["pattern_text"],
    )


def day_deviations(analysis: dict, date: dt.date) -> list[Deviation]:
    entry = _entry(analysis, date)
    return [_deviation(c) for c in entry["compare"]] if entry else []


def day_reasons(analysis: dict, date: dt.date) -> list[Reason]:
    entry = _entry(analysis, date)
    return [_reason(r) for r in entry["reasons"]] if entry else []


def explain_day(analysis: dict, date: dt.date) -> str | None:
    entry = _entry(analysis, date)
    if entry is None:
        return None
    if entry["reasons"]:
        return entry["reasons"][0]["text"]
    return entry["no_reason_text"]


def day_summary(analysis: dict, date: dt.date) -> DaySummary:
    entry = _entry(analysis, date) or {"label": None, "score": None, "reasons": [], "compare": []}
    deviations = [_deviation(c) for c in entry["compare"]]
    # same line as the day view: reason, else "no clear pattern" on good/bad days, else (neutral
    # or no check-in) the biggest difference from the average good day
    headline = explain_day(analysis, date) or (deviations[0].text if deviations else None)
    return DaySummary(
        date=date,
        label=entry["label"],
        score=entry["score"],
        top_deviations=deviations[:2],
        has_reason=bool(entry["reasons"]),
        headline=headline,
    )


def day_detail(analysis: dict, day: Day, survey: SurveyBase | None) -> DayDetail:
    entry = _entry(analysis, day.date)
    values = entry["values"] if entry else []
    searched = engine.search_features(analysis["info"]["group_e_feature"])
    return DayDetail(
        date=day.date,
        label=entry["label"] if entry else None,
        score=entry["score"] if entry else None,
        survey=survey,
        features=[
            FeatureValue(
                feature=v["feature"],
                label=v["label"],
                unit=v["unit"],
                value=v["value"],
                norm=_norm(v["norm"], v["reference"]),
                when=v["when"],
                display=v["display"],
                in_patterns=v["feature"] in searched,
            )
            for v in values
        ],
        deviations=day_deviations(analysis, day.date),
        summary=explain_day(analysis, day.date),
        reasons=day_reasons(analysis, day.date),
        outside_window=bool(entry and entry["outside_window"]),
    )


# ---------------------------------------------------------------- patterns + recipe
def _when(p: dict) -> str:
    night = C.FEATURES[p["feature"]].night
    if p["variant"] == "avg3":
        return "last_3_nights" if night else "previous_3_days"
    return "last_night" if night else "day_before"


def _condition(p: dict) -> str:
    amount = texts.fmt(p["feature"], p["threshold"])
    if p["feature"] == "bedtime_h":
        return f"{'before' if p['op'] == 'below' else 'after'} {amount}"
    if p["feature"] == "steps":
        return f"{'fewer' if p['op'] == 'below' else 'more'} than {amount} steps"
    return f"{'under' if p['op'] == 'below' else 'over'} {amount}"


def _stats(p: dict) -> dict:
    return {
        "level": p["level"],
        "when": _when(p),
        "threshold": p["threshold"],
        "days_in_condition": p["days_in_condition"],
        "target_days_in_condition": p["target_days_in_condition"],
        "rate_in": p["rate_in"],
        "rate_out": p["rate_out"],
        # significant: tested against all features; preliminary: against its own feature only
        "p_value": p["p_global"] if p["level"] == "significant" else p["p_feature"],
        "feature": p["feature"],
        "label": FEATURES[p["feature"]].label,
        "condition": _condition(p),
        "text": p["text"],
    }


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def _status_summary(analysis: dict, status: str, kind: str, n: int) -> str:
    have, needed = days_with_data(analysis)
    common = {
        "insufficient_days": f"Keep checking in: insights appear after {needed} days with watch "
        f"data and a check-in ({have} so far).",
        "insufficient_variation": "Your check-ins are very similar every day, so there is "
        "nothing to compare yet.",
        "preliminary": f"No clear pattern yet, but {_plural(n, 'early signal')} "
        f"{'is' if n == 1 else 'are'} worth watching.",
    }
    if status in common:
        return common[status]
    if kind == "bad":
        return {
            "ok": f"We found {_plural(n, 'possible reason')} behind your bad days.",
            "not_enough_evidence": "Your bad days don't share a clear pattern in your watch "
            "data yet.",
            "insufficient_bad_days": "Not enough bad days yet to look for patterns.",
        }[status]
    return {
        "ok": f"Your good days usually share {_plural(n, 'thing')}.",
        "not_enough_evidence": "Your good days don't share a clear recipe in your watch data yet.",
        "insufficient_good_days": "Not enough good days yet to write your recipe.",
    }[status]


def bad_day_patterns(analysis: dict) -> PatternReport:
    group = analysis["patterns"]["bad"]
    patterns = [
        Pattern(
            **_stats(p),
            bad_share=p["share_bad"],
            good_share=p["share_good"],
            example_dates=p["example_dates"],
        )
        for p in group["patterns"]
    ]
    return PatternReport(
        status=group["status"],
        summary=_status_summary(analysis, group["status"], "bad", len(patterns)),
        bad_days_count=analysis["info"]["n_bad_window"],
        patterns=patterns,
    )


def good_day_recipe(analysis: dict) -> Recipe:
    group = analysis["patterns"]["good"]
    ingredients = [Ingredient(**_stats(p), good_share=p["share_good"]) for p in group["patterns"]]
    return Recipe(
        status=group["status"],
        summary=_status_summary(analysis, group["status"], "good", len(ingredients)),
        good_days_count=analysis["info"]["n_good_window"],
        ingredients=ingredients,
    )
