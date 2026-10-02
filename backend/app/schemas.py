from datetime import UTC, datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.models import ItemBase


class ItemCreate(ItemBase):
    pass


class ItemUpdate(SQLModel):
    """All fields optional; only fields sent by the client are applied (PATCH)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def name_not_null(cls, value: str | None) -> str:
        # Runs only when the client sends "name"; omitting it is fine, sending null is not.
        if value is None:
            raise ValueError("name cannot be null")
        return value


class ItemRead(ItemBase):
    id: int
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def assume_utc(cls, value: datetime) -> datetime:
        # SQLite drops tzinfo; mark it as UTC so the JSON carries an offset for the frontend.
        return value if value.tzinfo else value.replace(tzinfo=UTC)
