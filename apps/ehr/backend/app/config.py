"""
Application Configuration - Pydantic Settings

All configuration lives here. Values are read, in priority order, from:
1. Environment variables (e.g. the `environment:` block in docker-compose.yml)
2. The .env file in the backend directory
3. Defaults defined below

Fields without a default are required: the app refuses to start without them.

USAGE
=====
    from app.config import settings

    settings.DATABASE_URL
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================================================================
    # Database Configuration
    # =========================================================================
    # Required. Format: postgresql+psycopg2://user:password@host:port/database
    # From .venv: localhost:5433. Inside Docker: postgres:5432.
    DATABASE_URL: str

    # =========================================================================
    # Application Settings
    # =========================================================================
    # "development" or "production"
    ENVIRONMENT: str = "development"

    # Enables detailed errors and SQL logging. NEVER True in production.
    DEBUG: bool = False

    # API version prefix
    API_VERSION: str = "v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore env vars not defined here (e.g. SECRET_KEY for now)
    )


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once; later calls return the cached instance."""
    return Settings()


settings = get_settings()
