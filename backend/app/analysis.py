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
    FeatureStats,
    FeatureValue,
    GroupAverage,
    Ingredient,
    InsightStatus,
    Label,
    NormRange,
    Pattern,
    PatternChart,
    PatternPoint,
    PatternReport,
    Reason,
    Recipe,
    Signal,
    StatsReport,
    SurveyRead,
    TimelinePoint,
    TimelineValue,
    TodayRead,
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


def pattern_features(analysis: dict) -> list[str]:
    return list(engine.search_features(analysis["info"]["group_e_feature"]))


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
        leans=c["leans"],
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


def _features(analysis: dict, entry: dict | None) -> list[FeatureValue]:
    searched = engine.search_features(analysis["info"]["group_e_feature"])
    return [
        FeatureValue(
            feature=v["feature"],
            label=v["label"],
            unit=v["unit"],
            value=v["value"],
            norm=_norm(v["norm"], v["reference"]),
            when=v["when"],
            display=v["display"],
            in_patterns=v["feature"] in searched,
            leans=v["leans"],
        )
        for v in (entry["values"] if entry else [])
    ]


def day_detail(analysis: dict, day: Day, survey: SurveyBase | None) -> DayDetail:
    entry = _entry(analysis, day.date)
    return DayDetail(
        date=day.date,
        label=entry["label"] if entry else None,
        score=entry["score"] if entry else None,
        survey=survey,
        features=_features(analysis, entry),
        deviations=day_deviations(analysis, day.date),
        summary=explain_day(analysis, day.date),
        reasons=day_reasons(analysis, day.date),
        outside_window=bool(entry and entry["outside_window"]),
        timeline=timeline(analysis, day.date),
    )


# offsets (relative to the viewed day) whose data a reason with this window uses
WINDOW_OFFSETS = {
    "lag1": {True: [0], False: [-1]},
    "avg3": {True: [-2, -1, 0], False: [-3, -2, -1]},
}


def timeline(analysis: dict, date: dt.date) -> list[TimelinePoint]:
    entry = _entry(analysis, date)
    # last night ended after the check-in: the analysis did not use it, so don't show it either
    late = bool(entry and entry["late_night"])
    highlight: dict[int, set[str]] = {}
    for r in entry["reasons"] if entry else []:
        for offset in WINDOW_OFFSETS[r["when"]][C.FEATURES[r["feature"]].night]:
            if not (late and offset == 0):
                highlight.setdefault(offset, set()).add(r["feature"])
    points = []
    for offset in range(-3, 1):
        d = date + dt.timedelta(days=offset)
        e = _entry(analysis, d)
        raw = e["raw"] if e else {"night": {}, "activity": {}}
        if late and offset == 0:
            raw = {"night": {}, "activity": raw["activity"]}

        def values(part: str, offset: int = offset, raw: dict = raw) -> list[TimelineValue]:
            return [
                TimelineValue(
                    feature=name,
                    label=FEATURES[name].label,
                    unit=FEATURES[name].unit,
                    value=value,
                    display=texts.fmt(name, value),
                    highlight=name in highlight.get(offset, set()),
                )
                for name, value in raw[part].items()
            ]

        points.append(
            TimelinePoint(
                date=d,
                offset=offset,
                label=e["label"] if e else None,
                night=values("night"),
                activity=values("activity"),
            )
        )
    return points


def label_stats(analysis: dict) -> StatsReport:
    """Average of every feature on good vs bad days (the days patterns are searched on)."""
    info = analysis["info"]
    searched = engine.search_features(info["group_e_feature"])
    empty = {"n": 0, "mean": None}

    def group(name: str, g: dict) -> GroupAverage:
        mean = g["mean"]
        return GroupAverage(
            average=round(mean, 3) if mean is not None else None,
            display=texts.fmt(name, mean) if mean is not None else None,
            days=g["n"],
        )

    features = []
    for name, f in C.FEATURES.items():
        s = analysis["stats"].get(name, {"good": empty, "bad": empty})
        good, bad = group(name, s["good"]), group(name, s["bad"])
        both = good.average is not None and bad.average is not None
        features.append(
            FeatureStats(
                feature=name,
                label=f.label,
                unit=f.unit,
                when="last_night" if f.night else "day_before",
                in_patterns=name in searched,
                good=good,
                bad=bad,
                difference=round(bad.average - good.average, 3) if both else None,
            )
        )
    return StatsReport(
        analysed_days=info["n_window_days"],
        date_from=info["window_first_date"],
        date_to=info["window_last_date"],
        good_days_count=info["n_good_window"],
        bad_days_count=info["n_bad_window"],
        features=features,
    )


# ---------------------------------------------------------------- today (home screen)
def _signal(s: dict) -> Signal:
    return Signal(
        kind=s["kind"],
        feature=s["feature"],
        label=FEATURES[s["feature"]].label,
        value=s["value"],
        display=texts.fmt(s["feature"], s["value"]),
        when=_when({"feature": s["feature"], "variant": s["when"]}),
        text=texts.signal_text(s["kind"], s["value_text"]),
        pattern_text=s["pattern_text"],
    )


def today(analysis: dict, morning: dict, date: dt.date, survey: SurveyRead | None) -> TodayRead:
    """analysis: current data; morning: the same data without today's check-in (signals).

    Signals use only data known before the check-in (last night, the day before) and patterns
    found without today's answers, so the morning heads-up stays put after the check-in.
    """
    early = _entry(morning, date)
    heads_up = [_signal(s) for s in early["signals"]["bad"]] if early else []
    good_signs = [_signal(s) for s in early["signals"]["good"]] if early else []
    has_watch_data = bool(early) and any(v["value"] is not None for v in early["values"])
    if not has_watch_data:
        outlook = "unknown"
    elif heads_up and good_signs:
        outlook = "mixed"
    else:
        outlook = "tough" if heads_up else "promising" if good_signs else "neutral"
    if survey is not None:
        summary = explain_day(analysis, date) or texts.CHECKIN_SAVED
    else:
        summary = texts.OUTLOOK[outlook]
    return TodayRead(
        date=date,
        has_watch_data=has_watch_data,
        survey=survey,
        outlook=outlook,
        summary=summary,
        heads_up=heads_up,
        good_signs=good_signs,
        deviations=[_deviation(c) for c in early["compare"]] if early else [],
        features=_features(morning, early),
    )


# ---------------------------------------------------------------- patterns + recipe
def _when(p: dict) -> str:
    night = C.FEATURES[p["feature"]].night
    if p["variant"] == "avg3":
        return "last_3_nights" if night else "previous_3_days"
    return "last_night" if night else "day_before"


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
        "condition": texts.pattern_condition(p),
        "text": p["text"],
    }


def _status_summary(analysis: dict, status: str, kind: str, n: int) -> str:
    have, needed = days_with_data(analysis)
    return texts.status_summary(status, kind, n, have, needed)


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


def pattern_chart(analysis: dict, feature: str, kind: str) -> PatternChart | None:
    """The persona's pattern for `feature` of this kind (significant or early signal)."""
    p = next((p for p in analysis["patterns"][kind]["patterns"] if p["feature"] == feature), None)
    if p is None:
        return None
    return PatternChart(
        **_stats(p),
        kind=kind,
        unit=FEATURES[feature].unit,
        op=p["op"],
        variant=p["variant"],
        display_threshold=texts.fmt(feature, p["threshold"]),
        points=[
            PatternPoint(
                date=pt["date"],
                value=pt["value"],
                display=texts.fmt(feature, pt["value"]),
                label=pt["label"],
                in_condition=pt["in_condition"],
            )
            for pt in p["points"]
        ],
    )
