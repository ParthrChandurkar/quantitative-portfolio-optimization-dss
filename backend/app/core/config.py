"""Environment-backed OptiVest application settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://optivest:optivest@localhost:5432/optivest",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="development-only-change-me", alias="JWT_SECRET")
    jwt_access_expiry: int = Field(default=900, alias="JWT_ACCESS_EXPIRY", ge=60)
    jwt_refresh_expiry: int = Field(
        default=2_592_000, alias="JWT_REFRESH_EXPIRY", ge=300
    )
    covariance_lookback_days: int = Field(
        default=252, alias="COVARIANCE_LOOKBACK_DAYS", ge=2
    )
    debug: bool = Field(default=False, alias="DEBUG")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.casefold()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "dev"}:
                return True
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
