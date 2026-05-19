"""
Application Configuration - Pydantic Settings

This module centralizes ALL configuration in one place using Pydantic Settings.

WHY USE PYDANTIC SETTINGS?
==========================
1. VALIDATION AT STARTUP
   - If a required env var is missing, the app won't start
   - You find out immediately, not at 3am when a customer tries to pay
   
2. TYPE CONVERSION
   - Automatically converts "30" → 30 (string to int)
   - Booleans from "true", "1", "yes" → True
   
3. SINGLE SOURCE OF TRUTH
   - All config in one place
   - Easy to see what the app needs to run
   
4. DEFAULT VALUES
   - Sensible defaults for development
   - Override with env vars in production

HOW IT WORKS
============
Pydantic Settings automatically reads from:
1. Environment variables (highest priority)
2. .env file (if present)
3. Default values in this file (lowest priority)

USAGE
=====
    from app.config import settings
    
    # Access any setting
    database_url = settings.DATABASE_URL
    debug_mode = settings.DEBUG
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Required vs Optional:
    - Fields without defaults are REQUIRED (app won't start without them)
    - Fields with defaults are optional (will use default if not set)
    """
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    # Required: Your PostgreSQL connection string
    # Format: postgresql+psycopg2://user:password@host:port/database
    DATABASE_URL: str
    
    # =========================================================================
    # Security / JWT Configuration
    # =========================================================================
    # Required: Secret key for signing JWT tokens
    # Generate with: openssl rand -hex 32
    # IMPORTANT: Use a different value in production!
    SECRET_KEY: str
    
    # JWT algorithm (don't change unless you know what you're doing)
    ALGORITHM: str = "HS256"
    
    # How long access tokens are valid (in minutes)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # =========================================================================
    # Application Settings
    # =========================================================================
    # Debug mode: enables detailed error messages
    # NEVER set to True in production (exposes sensitive info)
    DEBUG: bool = False
    
    # API version prefix
    API_VERSION: str = "v1"
    
    # Frontend URL (for CORS, email links, payment redirects)
    FRONTEND_URL: str = "http://localhost:5173"
    
    # =========================================================================
    # Superadmin (Initial Setup)
    # =========================================================================
    # These are used to create the initial superadmin account
    SUPERADMIN_USERNAME: str = "admin"
    SUPERADMIN_PASSWORD: str = "changeme"  # Change in production!
    SUPERADMIN_EMAIL: str = "admin@example.com"
    
    # =========================================================================
    # S3 / File Storage Configuration
    # =========================================================================
    # For local development, we use LocalStack (fake AWS)
    # In production, use real AWS S3 or another S3-compatible service
    
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:4566"  # LocalStack URL
    S3_BUCKET_NAME: str = "recipe-images"
    AWS_ACCESS_KEY_ID: str = "test"  # LocalStack doesn't check these
    AWS_SECRET_ACCESS_KEY: str = "test"
    AWS_REGION: str = "us-east-1"
    
    # =========================================================================
    # Email Configuration (Resend)
    # =========================================================================
    # Get your API key from https://resend.com/api-keys
    RESEND_API_KEY: Optional[str] = None  # Optional for local dev
    FROM_EMAIL: str = "onboarding@resend.dev"
    
    # =========================================================================
    # Payment Configuration (Stripe)
    # =========================================================================
    # Get your keys from https://dashboard.stripe.com/test/apikeys
    # sk_test_xxx for testing, sk_live_xxx for production
    STRIPE_SECRET_KEY: Optional[str] = None  # Optional for local dev
    
    # Webhook signing secret from `stripe listen` or Stripe Dashboard
    STRIPE_WEBHOOK_SECRET: Optional[str] = None  # Optional for local dev
    
    # =========================================================================
    # Pydantic Settings Configuration
    # =========================================================================
    model_config = SettingsConfigDict(
        # Load from .env file in the backend directory
        env_file=".env",
        # .env file is optional (we might have env vars set directly)
        env_file_encoding="utf-8",
        # Don't fail if .env file doesn't exist
        extra="ignore",  # Ignore extra env vars not defined here
    )


# =============================================================================
# Settings Singleton
# =============================================================================
# We use @lru_cache to ensure we only load settings once.
# This is important because:
# 1. Reading .env file is slow (disk I/O)
# 2. We want consistent settings throughout the app
# 3. Validation only needs to happen once at startup

@lru_cache
def get_settings() -> Settings:
    """
    Get the application settings (cached).
    
    First call: Loads from env vars/.env file, validates everything
    Subsequent calls: Returns cached settings instantly
    
    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()


# Create a global settings instance for easy importing
# Usage: from app.config import settings
settings = get_settings()
