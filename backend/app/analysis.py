import datetime as dt
import statistics
from dataclasses import dataclass

from app.models import Day
from app.schemas import (
    Deviation,
    Direction,
    Ingredient,
    Label,
    NormRange,
    Pattern,
    PatternReport,
    Recipe,
)


@dataclass(frozen=True)
class FeatureInfo:
    label: str
    unit: str


FEATURES: dict[str, FeatureInfo] = {
    "sleep_minutes": FeatureInfo("Sleep", "min"),
    "resting_hr": FeatureInfo("Resting heart rate", "bpm"),
    "steps": FeatureInfo("Steps", "steps"),
    "active_minutes": FeatureInfo("Active minutes", "min"),
    "calories": FeatureInfo("Calories burned", "kcal"),
}


def score_day(day: Day) -> float | None:
    answers = [
        answer
        for answer in (day.mood, day.fatigue, day.sleep_quality, day.stress)
        if answer is not None
    ]
    if len(answers) < 4:
        return None
    return round(statistics.fmean(answers), 2)


def label_day(day: Day) -> Label | None:
    score = score_day(day)
    if score is None:
        return None
    if score >= 3.5:
        return "good"
    if score <= 2.5:
        return "bad"
    return "neutral"


def personal_norm(days: list[Day]) -> dict[str, NormRange]:
    good_days = _days_with_label(days, "good")
    norm: dict[str, NormRange] = {}
    for feature in FEATURES:
        values = _values(good_days, feature)
        if len(values) < 3:
            continue
        low, median, high = statistics.quantiles(values, n=4)
        norm[feature] = NormRange(median=round(median, 1), low=round(low, 1), high=round(high, 1))
    return norm


def day_deviations(days: list[Day], date: dt.date) -> list[Deviation]:
    day = _find_day(days, date)
    if day is None:
        return []
    deviations: list[Deviation] = []
    for feature, norm in personal_norm(days).items():
        value = getattr(day, feature)
        if value is None:
            continue
        difference = value - norm.median
        z = difference / max(norm.high - norm.low, 1.0)
        if abs(z) < 0.75:
            continue
        direction: Direction = "higher" if difference > 0 else "lower"
        deviations.append(
            Deviation(
                feature=feature,
                label=FEATURES[feature].label,
                unit=FEATURES[feature].unit,
                value=value,
                norm=norm,
                difference=round(difference, 1),
                z=round(z, 2),
                direction=direction,
                text=_deviation_text(feature, difference),
            )
        )
    return sorted(deviations, key=lambda deviation: abs(deviation.z), reverse=True)


def explain_day(days: list[Day], date: dt.date) -> str | None:
    day = _find_day(days, date)
    if day is None:
        return None
    deviations = day_deviations(days, date)
    if deviations:
        return f"{deviations[0].text}."
    if label_day(day) == "bad":
        return "Your data looked close to your good days - the reason may be outside the watch."
    return "Nothing stood out - this day looked like your usual good days."


def bad_day_patterns(days: list[Day]) -> PatternReport:
    bad_days = _days_with_label(days, "bad")
    good_days = _days_with_label(days, "good")
    patterns: list[Pattern] = []
    for feature, norm in personal_norm(days).items():
        for side, low, high in (("below", None, norm.low), ("above", norm.high, None)):
            bad_share = _share(bad_days, feature, low, high)
            good_share = _share(good_days, feature, low, high)
            if bad_share < 0.4 or bad_share - good_share < 0.2:
                continue
            label = FEATURES[feature].label
            condition = f"{side} {_format_amount(feature, low if high is None else high)}"
            matching = [day for day in bad_days if _in_range(day, feature, low, high)]
            patterns.append(
                Pattern(
                    feature=feature,
                    label=label,
                    condition=condition,
                    bad_share=bad_share,
                    good_share=good_share,
                    text=f"On {bad_share:.0%} of your bad days, {label.lower()} was {condition}",
                    example_dates=[day.date for day in matching[-3:]],
                )
            )
    patterns.sort(key=lambda pattern: pattern.bad_share - pattern.good_share, reverse=True)
    if not bad_days:
        summary = "No bad days yet - keep checking in to find patterns."
    elif not patterns:
        summary = "Your bad days don't share a clear pattern yet."
    else:
        summary = f"We found {_plural(len(patterns), 'possible reason')} behind your bad days."
    return PatternReport(summary=summary, bad_days_count=len(bad_days), patterns=patterns)


def good_day_recipe(days: list[Day]) -> Recipe:
    good_days = _days_with_label(days, "good")
    bad_days = _days_with_label(days, "bad")
    scored: list[tuple[float, Ingredient]] = []
    for feature, norm in personal_norm(days).items():
        bad_values = _values(bad_days, feature)
        if not bad_values:
            continue
        more_is_better = norm.median >= statistics.median(bad_values)
        low, high = (norm.low, None) if more_is_better else (None, norm.high)
        good_share = _share(good_days, feature, low, high)
        bad_share = _share(bad_days, feature, low, high)
        if good_share - bad_share < 0.15:
            continue
        label = FEATURES[feature].label
        condition = (
            f"at least {_format_amount(feature, norm.low)}"
            if more_is_better
            else f"at most {_format_amount(feature, norm.high)}"
        )
        ingredient = Ingredient(
            feature=feature,
            label=label,
            condition=condition,
            good_share=good_share,
            text=f"{label}: {condition}",
        )
        scored.append((good_share - bad_share, ingredient))
    scored.sort(key=lambda item: item[0], reverse=True)
    ingredients = [ingredient for _, ingredient in scored[:5]]
    summary = (
        f"Your good days usually share {_plural(len(ingredients), 'thing')}."
        if ingredients
        else "Not enough good days yet to write your recipe."
    )
    return Recipe(summary=summary, good_days_count=len(good_days), ingredients=ingredients)


def _days_with_label(days: list[Day], label: Label) -> list[Day]:
    return [day for day in days if label_day(day) == label]


def _find_day(days: list[Day], date: dt.date) -> Day | None:
    return next((day for day in days if day.date == date), None)


def _values(days: list[Day], feature: str) -> list[float]:
    return [value for day in days if (value := getattr(day, feature)) is not None]


def _in_range(day: Day, feature: str, low: float | None, high: float | None) -> bool:
    value = getattr(day, feature)
    if value is None:
        return False
    return (low is None or value >= low) and (high is None or value <= high)


def _share(days: list[Day], feature: str, low: float | None, high: float | None) -> float:
    if not days:
        return 0.0
    return round(sum(_in_range(day, feature, low, high) for day in days) / len(days), 2)


def _format_amount(feature: str, amount: float) -> str:
    unit = FEATURES[feature].unit
    amount = abs(amount)
    if unit == "min" and amount >= 60:
        hours, minutes = divmod(round(amount), 60)
        return f"{hours}h{minutes:02d}"
    return f"{round(amount):,} {unit}"


def _deviation_text(feature: str, difference: float) -> str:
    amount = _format_amount(feature, difference)
    if feature == "sleep_minutes":
        return f"You slept {amount} {'more' if difference > 0 else 'less'} than on your good days"
    side = "above" if difference > 0 else "below"
    return f"{FEATURES[feature].label} was {amount} {side} your good-day level"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"
