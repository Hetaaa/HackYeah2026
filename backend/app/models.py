import datetime as dt

from sqlmodel import Field, SQLModel, UniqueConstraint


class Persona(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=100)
    description: str = Field(default="", max_length=500)


class FitbitBase(SQLModel):
    sleep_minutes: float | None = Field(
        default=None,
        description="Sleep from the night before this day",
        schema_extra={"examples": [452]},
    )
    resting_hr: float | None = Field(
        default=None, description="Resting heart rate", schema_extra={"examples": [58]}
    )
    steps: float | None = Field(default=None, schema_extra={"examples": [8400]})
    active_minutes: float | None = Field(default=None, schema_extra={"examples": [45]})
    calories: float | None = Field(default=None, schema_extra={"examples": [2350]})


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
