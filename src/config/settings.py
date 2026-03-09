"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Application
    app_name: str = "skyhigh-core"
    app_env: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://skyhigh:skyhigh123@localhost:5432/skyhigh_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Seat Hold Configuration
    seat_hold_duration_seconds: int = 120

    # Baggage Configuration
    max_baggage_weight_kg: float = 25.0
    excess_baggage_fee_per_kg: float = 10.0

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Cache
    cache_ttl_seconds: int = 30

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"



@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid reading .env file on every call.
    """
    return Settings()

