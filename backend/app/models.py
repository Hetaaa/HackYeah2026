import datetime as dt

from pydantic import NaiveDatetime
from sqlmodel import Field, SQLModel, UniqueConstraint


class Persona(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)
    analysis_window_end: dt.date | None = Field(
        default=None,
        description="Days from this date on are shown but not used to find patterns "
        "(PMData demo: 2020-03-12, COVID lockdown). None for real users.",
    )
    demo_today: dt.date | None = Field(
        default=None, description="Demo clock: the persona's 'today'. None = the real date"
    )
    demo_answers: str | None = Field(
        default=None,
        max_length=20,
        description="Demo only: real check-in of demo_today, 'mood,fatigue,sleep_quality,stress'",
    )
    position: int = Field(default=0, description="Order in the persona switcher")


class FitbitBase(SQLModel):
    """Watch data of one day. All optional: missing data is fine, the analysis skips it.

    Night fields describe the main sleep that ENDED on the morning of this date; activity fields
    describe this local calendar day (the analysis uses the day before the survey).
    Sleep times are the watch's local time (they carry the bedtime, so no UTC here).
    """

    # night ending this morning
    sleep_minutes: float | None = Field(
        default=None,
        description="Sleep from the night before this day",
        schema_extra={"examples": [452]},
    )
    sleep_start: NaiveDatetime | None = Field(default=None, description="Local time")
    sleep_end: NaiveDatetime | None = Field(default=None, description="Local time")
    sleep_type: str | None = Field(
        default=None, max_length=10, description='"stages" or "classic" (no sleep stages)'
    )
    time_in_bed_minutes: float | None = None
    sleep_efficiency: float | None = Field(default=None, description="Fitbit efficiency, %")
    wake_minutes: float | None = Field(default=None, description="Minutes awake during the night")
    wake_pct: float | None = Field(default=None, description="Minutes awake / time in bed, %")
    rem_pct: float | None = Field(default=None, description="REM sleep / sleep, %")
    deep_pct: float | None = Field(default=None, description="Deep sleep / sleep, %")
    sleep_hr_mean: float | None = Field(default=None, description="Mean heart rate during sleep")
    sleep_score: float | None = None
    resting_hr: float | None = Field(
        default=None, description="Resting heart rate", schema_extra={"examples": [58]}
    )
    # this calendar day
    steps: float | None = Field(default=None, schema_extra={"examples": [8400]})
    active_minutes: float | None = Field(
        default=None,
        description="Moderate + vigorous activity minutes",
        schema_extra={"examples": [45]},
    )
    light_minutes: float | None = Field(default=None, description="Light activity minutes")
    sedentary_minutes: float | None = None
    cardio_peak_minutes: float | None = Field(
        default=None, description="Minutes in cardio + peak heart-rate zones"
    )
    calories: float | None = Field(default=None, schema_extra={"examples": [2350]})
    wear_minutes: float | None = Field(
        default=None, description="Minutes with a heart-rate reading (00-24); None = unknown"
    )
    wear_minutes_day: float | None = Field(
        default=None,
        description="Worn minutes 06-24; under 720 the day's activity is ignored. None = unknown",
    )


class SurveyBase(SQLModel):
    mood: int = Field(ge=1, le=5, schema_extra={"examples": [4]})
    fatigue: int = Field(ge=1, le=5, schema_extra={"examples": [3]})
    sleep_quality: int = Field(ge=1, le=5, schema_extra={"examples": [4]})
    stress: int = Field(ge=1, le=5, schema_extra={"examples": [3]})


class Day(FitbitBase, table=True):
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="persona.id", index=True)
    date: dt.date
    mood: int | None = Field(default=None, ge=1, le=5)
    fatigue: int | None = Field(default=None, ge=1, le=5)
    sleep_quality: int | None = Field(default=None, ge=1, le=5)
    stress: int | None = Field(default=None, ge=1, le=5)
    survey_at: dt.datetime | None = Field(
        default=None, description="When the survey was filled (UTC); None = assume 08:00 local"
    )
