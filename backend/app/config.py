from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    # NoDecode: read the raw env string instead of expecting JSON, then split on commas below.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    env: str = "dev"
    # POST /api/demo/reset restores the demo personas; opt-in so a public deploy can't be wiped
    demo_reset: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
