import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.models import SurveyBase

Label = Literal["good", "neutral", "bad"]
Direction = Literal["higher", "lower"]


class ErrorRead(BaseModel):
    detail: str = Field(examples=["Persona p99 not found"])


class PersonaRead(BaseModel):
    id: str = Field(examples=["p01"])
    name: str = Field(examples=["Alex"])
    description: str = Field(examples=["Bad days tend to follow short nights."])
    first_date: dt.date | None = Field(examples=["2019-11-01"])
    last_date: dt.date | None = Field(examples=["2020-03-29"])
    days_count: int = Field(examples=[150])


class NormRange(BaseModel):
    median: float = Field(description="Median on good days", examples=[455])
    low: float = Field(description="25th percentile on good days", examples=[430])
    high: float = Field(description="75th percentile on good days", examples=[480])


class FeatureValue(BaseModel):
    feature: str = Field(examples=["sleep_minutes"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["min"])
    value: float | None = Field(examples=[352])
    norm: NormRange | None


class Deviation(BaseModel):
    feature: str = Field(examples=["sleep_minutes"])
    label: str = Field(examples=["Sleep"])
    unit: str = Field(examples=["min"])
    value: float = Field(examples=[352])
    norm: NormRange
    difference: float = Field(description="value - norm.median", examples=[-103])
    z: float = Field(description="Signed size of the deviation, sorted by abs", examples=[-2.06])
    direction: Direction
    text: str = Field(examples=["You slept 1h43 less than on your good days"])


class DaySummary(BaseModel):
    date: dt.date
    label: Label | None = Field(description="null when the survey is missing")
    score: float | None = Field(examples=[2.25])
    top_deviations: list[Deviation] = Field(description="Up to 2 biggest deviations")


class DayDetail(BaseModel):
    date: dt.date
    label: Label | None
    score: float | None = Field(examples=[2.25])
    survey: SurveyBase | None
    features: list[FeatureValue]
    deviations: list[Deviation]
    summary: str | None = Field(examples=["You slept 1h43 less than on your good days."])


class Pattern(BaseModel):
    feature: str = Field(examples=["sleep_minutes"])
    label: str = Field(examples=["Sleep"])
    condition: str = Field(examples=["below 7h10"])
    bad_share: float = Field(description="Share of bad days matching", examples=[0.71])
    good_share: float = Field(description="Share of good days matching", examples=[0.18])
    text: str = Field(examples=["On 71% of your bad days, sleep was below 7h10"])
    example_dates: list[dt.date]


class PatternReport(BaseModel):
    summary: str = Field(examples=["We found 2 possible reasons behind your bad days."])
    bad_days_count: int = Field(examples=[24])
    patterns: list[Pattern]


class Ingredient(BaseModel):
    feature: str = Field(examples=["steps"])
    label: str = Field(examples=["Steps"])
    condition: str = Field(examples=["at least 7,800 steps"])
    good_share: float = Field(description="Share of good days matching", examples=[0.8])
    text: str = Field(examples=["Steps: at least 7,800 steps"])


class Recipe(BaseModel):
    summary: str = Field(examples=["Your good days usually share these 3 things."])
    good_days_count: int = Field(examples=[90])
    ingredients: list[Ingredient]


class SurveyCreate(SurveyBase):
    pass


class SurveyRead(SurveyBase):
    date: dt.date
    label: Label | None
    score: float | None = Field(examples=[3.5])
