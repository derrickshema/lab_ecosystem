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
    # JWT Signing (RS256: private key signs, public key verifies)
    # =========================================================================
    # Only this service holds the private key. Other apps verify tokens with
    # the public key, published at GET /.well-known/jwks.json.
    # Generate both with: python -m scripts.generate_jwt_keys
    JWT_PRIVATE_KEY_PATH: str = "keys/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/jwt_public.pem"
    # Key ID put in each token header, so verifiers can pick the right key
    # after a rotation. Change it whenever you generate a new key pair.
    JWT_KEY_ID: str = "identity-dev-1"
    # "iss" claim; verifiers reject tokens from any other issuer
    JWT_ISSUER: str = "lab-identity"
    ALGORITHM: str = "RS256"

    # How long access tokens are valid (in minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # How long refresh tokens are valid (in minutes) — default 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # How long password reset tokens are valid (in minutes)
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # How long email verification tokens are valid (in minutes) — default 24 hours
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # =========================================================================
    # Application Settings
    # =========================================================================
    # Enables detailed errors and SQL logging, and non-Secure cookies over HTTP.
    # NEVER True in production.
    DEBUG: bool = False

    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:5173"

    # =========================================================================
    # Superadmin (Initial Setup) — used by scripts/create_superadmin.py
    # =========================================================================
    SUPERADMIN_USERNAME: str = "admin"
    SUPERADMIN_PASSWORD: str = "changeme"  # Change in production!
    SUPERADMIN_EMAIL: str = "admin@example.com"

    # =========================================================================
    # Email Configuration (Resend)
    # =========================================================================
    # Get your API key from https://resend.com/api-keys
    RESEND_API_KEY: str | None = None  # Optional for local dev: emails are logged instead
    FROM_EMAIL: str = "onboarding@resend.dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore env vars not defined here
    )


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once; later calls return the cached instance."""
    return Settings()


settings = get_settings()
