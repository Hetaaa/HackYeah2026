import datetime as dt
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.models import SurveyBase

Label = Literal["good", "neutral", "bad"]
Direction = Literal["higher", "lower"]
Lean = Literal["bad", "good"]
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


class PersonaCreate(BaseModel):
    """Onboarding: a new real user (watch data and check-ins come later)."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = (
        Field(examples=["Maja"])
    )
    description: str = Field(default="", max_length=500, examples=[""])


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
    pattern_features: list[str] = Field(
        default_factory=list,
        description="Features this user's patterns are searched on (the exercise feature is "
        "z_cardio_peak or mvpa, depending on the data)",
        examples=[["sleep_h", "bedtime_h", "wake_pct", "steps", "z_cardio_peak", "lightly"]],
    )
    demo_answers: SurveyBase | None = Field(
        default=None, description="Demo only: the real check-in of `today`, to prefill sliders"
    )


class NormRange(BaseModel):
    """Reference days: good days, or all days with < 10 good days (PersonaRead.norm_reference)."""

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
    display: str | None = Field(default=None, examples=["5h54"])
    in_patterns: bool = Field(
        default=True, description="False: shown for context only, never used as a reason"
    )
    leans: Lean | None = Field(
        default=None,
        description="bad: differs from the reference in the direction of this user's bad days "
        "(e.g. their bad days have less sleep and this is less); good: towards their good days. "
        "From the user's own good vs bad day averages, not health advice. null: fewer than 5 "
        "good or bad days, or good and bad days look alike for this feature",
    )


class Deviation(BaseModel):
    """Descriptive comparison with the average good day, or the average day with < 10 good
    days (PersonaRead.norm_reference). Not a cause."""

    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["h"])
    value: float = Field(examples=[5.9])
    norm: NormRange
    difference: float = Field(description="value - norm.average", examples=[-1.7])
    z: float = Field(description="Signed size in SDs of good days, sorted by abs", examples=[-2.06])
    direction: Direction
    leans: Lean | None = Field(
        default=None,
        description="bad: differs from the reference in the direction of this user's bad days "
        "(e.g. their bad days have less sleep and this is less); good: towards their good days. "
        "From the user's own good vs bad day averages, not health advice. null: fewer than 5 "
        "good or bad days, or good and bad days look alike for this feature",
    )
    text: str = Field(examples=["Sleep -1h43 vs good days"])


class Reason(BaseModel):
    """A day's possible reason: a significant personal pattern whose condition held that day."""

    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    value: float = Field(examples=[5.3])
    display: str = Field(examples=["5h19"])
    text: str = Field(examples=["Possible reason: 5h19 sleep"])
    pattern_text: str = Field(examples=["Under 6h sleep: 11 of 14 days bad"])


class DaySummary(BaseModel):
    date: dt.date
    label: Label | None = Field(description="null when the survey is missing")
    score: float | None = Field(
        examples=[-1.2],
        description="Check-in score, 0 = typical day (see PersonaRead.label_mode)",
    )
    top_deviations: list[Deviation] = Field(description="Up to 2 biggest deviations")
    has_reason: bool = Field(default=False, description="A possible reason exists for this day")
    headline: str | None = Field(
        default=None,
        description="Possible reason, else the biggest difference from the average good day "
        "(descriptive, not a cause), else 'No clear reason' on good/bad days",
    )


class TimelineValue(BaseModel):
    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["h"])
    value: float = Field(examples=[5.3])
    display: str = Field(examples=["5h19"])
    highlight: bool = Field(description="Used by this day's possible reason")


class TimelinePoint(BaseModel):
    """One of the 4 days D-3..D in the day view."""

    date: dt.date
    offset: int = Field(description="-3..0, 0 = the viewed day", examples=[-1])
    label: Label | None
    night: list[TimelineValue] = Field(description="Sleep that ended on the morning of `date`")
    activity: list[TimelineValue] = Field(description="Activity of the calendar day `date`")


class DayDetail(BaseModel):
    date: dt.date
    label: Label | None
    score: float | None = Field(examples=[-1.2])
    survey: SurveyBase | None
    features: list[FeatureValue]
    deviations: list[Deviation] = Field(description="Compared with your average good day")
    summary: str | None = Field(
        examples=["Possible reason: 5h19 sleep"],
        description="First reason, or 'No clear reason' on good/bad days without one",
    )
    reasons: list[Reason] = Field(default_factory=list, description="Up to 2 possible reasons")
    outside_window: bool = Field(
        default=False, description="Day after the analysis window (shown, not used for patterns)"
    )
    timeline: list[TimelinePoint] = Field(
        default_factory=list,
        description="D-3..D: nights and activity behind this day; `highlight` marks the data "
        "the possible reason comes from (last night = night of D, the day before = activity "
        "of D-1, 3-day averages = 3 points)",
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
    condition: str = Field(examples=["Under 6h sleep"])
    bad_share: float = Field(description="Share of bad days matching", examples=[0.71])
    good_share: float = Field(description="Share of good days matching", examples=[0.18])
    text: str = Field(examples=["Under 6h sleep: 11 of 14 days bad"])
    example_dates: list[dt.date]


class PatternPoint(BaseModel):
    date: dt.date
    value: float = Field(examples=[13.3])
    display: str = Field(examples=["13.3%"])
    label: Label
    in_condition: bool = Field(description="The pattern's condition held on this day")


class PatternChart(PatternStats):
    """Data behind one pattern: every analysed day's value against the threshold."""

    kind: Literal["bad", "good"]
    feature: str = Field(examples=["wake_pct"])
    label: str = Field(examples=["Awake at night"])
    unit: str = Field(examples=["%"])
    op: Literal["below", "above"] = Field(description="Condition side of the threshold")
    variant: Literal["lag1", "avg3"] = Field(description="Single night/day or 3-day average")
    condition: str = Field(examples=["Awake over 12% of night"])
    display_threshold: str = Field(examples=["12%"])
    text: str
    points: list[PatternPoint] = Field(description="Analysed days (analysis window) in date order")


class PatternReport(BaseModel):
    status: InsightStatus = "ok"
    summary: str = Field(examples=["2 possible reasons for bad days"])
    bad_days_count: int = Field(examples=[24])
    patterns: list[Pattern]


class Ingredient(PatternStats):
    feature: str = Field(examples=["steps"])
    label: str = Field(examples=["Steps"])
    condition: str = Field(examples=["Over 3k steps (3-day avg)"])
    good_share: float = Field(description="Share of good days matching", examples=[0.8])
    text: str = Field(examples=["Over 3k steps (3-day avg): 9 of 14 days good"])


class Recipe(BaseModel):
    status: InsightStatus = "ok"
    summary: str = Field(examples=["3 things your good days share"])
    good_days_count: int = Field(examples=[90])
    ingredients: list[Ingredient]


class GroupAverage(BaseModel):
    average: float | None = Field(
        description="Mean in the feature's unit; null with fewer than 3 days", examples=[7.4]
    )
    display: str | None = Field(examples=["7 h 24 min"])
    days: int = Field(description="Days with a value", examples=[24])


class FeatureStats(BaseModel):
    feature: str = Field(examples=["sleep_h"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["h"])
    when: When = Field(description="Which data the averages describe")
    in_patterns: bool = Field(description="False: shown for context only, never a reason")
    good: GroupAverage = Field(description="Average on good days")
    bad: GroupAverage = Field(description="Average on bad days")
    difference: float | None = Field(
        description="bad.average - good.average (null when either is missing)", examples=[-1.1]
    )


class StatsReport(BaseModel):
    """Every feature's average on good vs bad days: descriptive, no significance test."""

    analysed_days: int = Field(description="Days with a check-in and watch data", examples=[68])
    date_from: dt.date | None = Field(description="First analysed day", examples=["2019-11-05"])
    date_to: dt.date | None = Field(description="Last analysed day", examples=["2020-02-14"])
    good_days_count: int = Field(examples=[22])
    bad_days_count: int = Field(examples=[20])
    features: list[FeatureStats]


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
    text: str = Field(examples=["Heads-up: awake 13.3% of night"])
    pattern_text: str = Field(examples=["Awake over 12% of night: 15 of 27 days bad"])


class TodayRead(BaseModel):
    """Home screen: what last night and yesterday say about today, before and after check-in."""

    date: dt.date
    has_watch_data: bool = Field(description="Last night's sleep or yesterday's activity synced")
    survey: SurveyRead | None = Field(description="null until today's check-in is filled")
    outlook: Literal["tough", "promising", "mixed", "neutral", "unknown"] = Field(
        description="tough: only heads-ups; promising: only good signs; mixed: both; "
        "neutral: none; unknown: no watch data"
    )
    summary: str = Field(examples=["Tougher day possible"])
    heads_up: list[Signal] = Field(description="Bad-day patterns triggered (max 2)")
    good_signs: list[Signal] = Field(description="Good-day patterns triggered (max 2)")
    deviations: list[Deviation] = Field(description="Compared with your average good day")
    features: list[FeatureValue]


class DemoReset(BaseModel):
    personas: int = Field(description="Demo personas restored", examples=[4])
    days: int = Field(description="Days of the demo personas", examples=[477])


class FeatureRead(BaseModel):
    feature: str = Field(examples=["wake_pct"])
    label: str = Field(examples=["Awake at night"])
    unit: str = Field(examples=["%"], description="h, clock, %, bpm, steps, min, pts")
    group: str = Field(examples=["C"])
    group_label: str = Field(examples=["Sleep continuity"])
    when: Literal["last_night", "day_before"] = Field(
        description="What a day's value refers to: the night before it or the previous day"
    )
    tested_direction: Direction = Field(
        description="Which direction the algorithm tests as linked to bad days, e.g. 'lower' "
        "sleep, 'higher' night heart rate. A per-person hypothesis, NOT health advice: "
        "a pattern exists only if the person's own data confirm it."
    )
    can_be_pattern: bool = Field(
        description="Can become a pattern / possible reason (else context only). mvpa and "
        "z_cardio_peak are alternatives: each user uses one, see PersonaRead.pattern_features"
    )
    description: str
