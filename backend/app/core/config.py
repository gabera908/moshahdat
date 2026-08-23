"""Application settings loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the FastAPI application."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Video Platform API"
    app_version: str = "1.0.0"

    database_url: str = "sqlite:///./local_dev.db"
    log_level: str = "INFO"

    jwt_secret: str = "dev-only-secret-change-me-in-production-0001"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    cors_origins: str = "http://localhost:3000,http://localhost:8080"
    rate_limit_per_minute: int = 60

    admin_username: str = "admin"
    admin_email: str = "admin@example.com"
    admin_password: str = "change_me_admin_password"
    admin_full_name: str = "System Admin"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
