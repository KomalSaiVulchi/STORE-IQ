"""Application configuration settings."""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings for StoreIQ."""

    # Core
    app_name: str = "storeiq-api"
    log_level: str = "INFO"
    database_url: str
    redis_url: str
    kafka_bootstrap: str
    kafka_raw_topic: str = "raw_events"
    kafka_sessions_topic: str = "sessions"
    kafka_anomalies_topic: str = "anomalies"

    # Store
    store_timezone: str = "Asia/Kolkata"
    store_capacity: int = 120
    stale_feed_minutes: int = 10

    # Security
    api_key: str = ""
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    # Pipeline tuning
    frame_skip: int = 3
    uvicorn_workers: int = 1

    # Database pool
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
