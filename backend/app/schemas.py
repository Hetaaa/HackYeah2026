import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.models import SurveyBase

Label = Literal["good", "neutral", "bad"]
Direction = Literal["higher", "lower"]
When = Literal["last_night", "day_before", "last_3_nights", "previous_3_days"]
InsightStatus = Literal[
    "ok",  # significant patterns found
    "preliminary",  # only early signals: show with care, never used as a day's reason
    "not_enough_evidence",
    "insufficient_bad_days",
    "insufficient_good_days",
    "insufficient_days",  # new user: still collecting check-ins with watch data
    "insufficient_variation",  # check-ins are almost always the same
]


class ErrorRead(BaseModel):
    detail: str = Field(examples=["Persona p99 not found"])


class PersonaRead(BaseModel):
    id: str = Field(examples=["p01"])
    name: str = Field(examples=["Alex"])
    description: str = Field(examples=["Bad days tend to follow short nights."])
    first_date: dt.date | None = Field(examples=["2019-11-01"])
    last_date: dt.date | None = Field(examples=["2020-03-29"])
    days_count: int = Field(examples=[150])
    insights_status: InsightStatus = Field(
        default="ok", description="ok when patterns can be searched, otherwise why not"
    )
    days_with_data: int = Field(
        default=0, description="Days with a check-in and watch data", examples=[133]
    )
    days_needed: int = Field(default=60, description="Days needed for insights", examples=[60])
    label_mode: Literal["personal", "absolute"] = Field(
        default="personal",
        description="personal: labels and scores relative to the user's history; absolute: "
        "fewer than 14 check-ins (or identical answers), score = mean of mood/fatigue/stress - 3",
    )
    norm_reference: Literal["good_days", "all_days"] = Field(
        default="good_days",
        description="What norms and deviations compare with (all_days if < 10 good days)",
    )
    today: dt.date = Field(
        description="The persona's 'today' (demo clock for PMData personas, else the real date)",
        examples=["2020-02-14"],
    )
    is_demo: bool = Field(default=False, description="Persona replays recorded demo data")
    demo_answers: SurveyBase | None = Field(
        default=None, description="Demo only: the real check-in of `today`, to prefill sliders"
    )


class NormRange(BaseModel):
    median: float = Field(description="Median on good days", examples=[455])
    low: float = Field(description="25th percentile on good days", examples=[430])
    high: float = Field(description="75th percentile on good days", examples=[480])
    average: float | None = Field(
        default=None, description="Mean on good days (the 'average good day')", examples=[452]
    )


class FeatureValue(BaseModel):
    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["h"], description="h, clock, %, bpm, steps, min, pts")
    value: float | None = Field(
        examples=[5.9],
        description="In `unit`; unit 'clock' (bedtime) = hours since 18:00 the evening before "
        "(5.5 = 23:30). Use `display` for text.",
    )
    norm: NormRange | None
    when: When = Field(default="last_night", description="Which data the value describes")
    display: str | None = Field(default=None, examples=["5 h 54 min"])
    in_patterns: bool = Field(
        default=True, description="False: shown for context only, never used as a reason"
    )


class Deviation(BaseModel):
    """Descriptive comparison with the average good day (not a cause)."""

    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["h"])
    value: float = Field(examples=[5.9])
    norm: NormRange
    difference: float = Field(description="value - norm.average", examples=[-1.7])
    z: float = Field(description="Signed size in SDs of good days, sorted by abs", examples=[-2.06])
    direction: Direction
    text: str = Field(examples=["You slept 1 h 43 min less than on your average good day."])


class Reason(BaseModel):
    """A day's possible reason: a significant personal pattern whose condition held that day."""

    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    value: float = Field(examples=[5.3])
    display: str = Field(examples=["5 h 19 min"])
    text: str = Field(examples=["Possible reason: you slept 5 h 19 min last night."])
    pattern_text: str = Field(
        examples=["When you sleep under 6 h, 11 of 14 days were bad days (vs 21% otherwise)."]
    )


class DaySummary(BaseModel):
    date: dt.date
    label: Label | None = Field(description="null when the survey is missing")
    score: float | None = Field(
        examples=[-1.2],
        description="Check-in score, 0 = typical day (see PersonaRead.label_mode)",
    )
    top_deviations: list[Deviation] = Field(description="Up to 2 biggest deviations")
    has_reason: bool = Field(default=False, description="A possible reason exists for this day")
    headline: str | None = Field(default=None, description="Reason text, else first deviation")


class DayDetail(BaseModel):
    date: dt.date
    label: Label | None
    score: float | None = Field(examples=[-1.2])
    survey: SurveyBase | None
    features: list[FeatureValue]
    deviations: list[Deviation] = Field(description="Compared with your average good day")
    summary: str | None = Field(
        examples=["Possible reason: you slept 5 h 19 min last night."],
        description="First reason, or a 'no clear pattern' line on good/bad days without one",
    )
    reasons: list[Reason] = Field(default_factory=list, description="Up to 2 possible reasons")
    outside_window: bool = Field(
        default=False, description="Day after the analysis window (shown, not used for patterns)"
    )


class PatternStats(BaseModel):
    level: Literal["significant", "preliminary"] = Field(
        description="preliminary = early signal, show with care"
    )
    when: When
    threshold: float = Field(
        examples=[6.0], description="Same unit as FeatureValue.value (bedtime: hours since 18:00)"
    )
    days_in_condition: int = Field(description="Days on which the condition held", examples=[14])
    target_days_in_condition: int = Field(description="...of which bad (good) days", examples=[11])
    rate_in: float = Field(
        description="Bad (good) day rate when the condition held", examples=[0.79]
    )
    rate_out: float = Field(description="Bad (good) day rate otherwise", examples=[0.21])
    p_value: float = Field(description="Permutation p-value", examples=[0.02])


class Pattern(PatternStats):
    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    condition: str = Field(examples=["under 6 h"])
    bad_share: float = Field(description="Share of bad days matching", examples=[0.71])
    good_share: float = Field(description="Share of good days matching", examples=[0.18])
    text: str = Field(
        examples=["When you sleep under 6 h, 11 of 14 days were bad days (vs 21% otherwise)."]
    )
    example_dates: list[dt.date]


class PatternReport(BaseModel):
    status: InsightStatus = "ok"
    summary: str = Field(examples=["We found 2 possible reasons behind your bad days."])
    bad_days_count: int = Field(examples=[24])
    patterns: list[Pattern]


class Ingredient(PatternStats):
    feature: str = Field(examples=["steps"])
    label: str = Field(examples=["Steps"])
    condition: str = Field(examples=["more than 3,000 steps"])
    good_share: float = Field(description="Share of good days matching", examples=[0.8])
    text: str = Field(
        examples=[
            "When you walk more than 3,000 steps on average over the previous 3 days, "
            "9 of 14 days were good days (vs 21% otherwise)."
        ]
    )


class Recipe(BaseModel):
    status: InsightStatus = "ok"
    summary: str = Field(examples=["Your good days usually share these 3 things."])
    good_days_count: int = Field(examples=[90])
    ingredients: list[Ingredient]


class SurveyCreate(SurveyBase):
    pass


class SurveyRead(SurveyBase):
    date: dt.date
    label: Label | None
    score: float | None = Field(
        examples=[-1.2], description="Check-in score, 0 = typical day (see PersonaRead.label_mode)"
    )


class Signal(BaseModel):
    """A significant personal pattern already triggered before today's check-in."""

    kind: Literal["bad", "good"] = Field(description="bad = heads-up, good = good sign")
    feature: str = Field(examples=["wake_pct"])
    label: str = Field(examples=["Awake at night"])
    value: float = Field(examples=[13.3])
    display: str = Field(examples=["13.3%"])
    when: When
    text: str = Field(examples=["Heads-up: you were awake 13.3% of last night."])
    pattern_text: str = Field(
        examples=[
            "When you are awake over 12% of the night, 15 of 27 days were bad days "
            "(vs 15% otherwise)."
        ]
    )


class TodayRead(BaseModel):
    """Home screen: what last night and yesterday say about today, before and after check-in."""

    date: dt.date
    has_watch_data: bool = Field(description="Last night's sleep or yesterday's activity synced")
    survey: SurveyRead | None = Field(description="null until today's check-in is filled")
    outlook: Literal["tough", "promising", "mixed", "neutral", "unknown"] = Field(
        description="tough: only heads-ups; promising: only good signs; mixed: both; "
        "neutral: none; unknown: no watch data"
    )
    summary: str = Field(examples=["Today may be tougher than usual."])
    heads_up: list[Signal] = Field(description="Bad-day patterns triggered (max 2)")
    good_signs: list[Signal] = Field(description="Good-day patterns triggered (max 2)")
    deviations: list[Deviation] = Field(description="Compared with your average good day")
    features: list[FeatureValue]


class DemoReset(BaseModel):
    personas: int = Field(examples=[4])
    days: int = Field(examples=[477])
