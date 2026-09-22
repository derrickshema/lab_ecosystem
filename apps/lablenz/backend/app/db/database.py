"""
Database Configuration Module

This module sets up the SQLModel/SQLAlchemy database engine.
The engine is the core interface to the database - it manages
the connection pool and executes all database operations.
"""

from sqlmodel import create_engine

from ..config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,   # test connections before use — prevents stale connection errors
    pool_size=5,          # persistent connections kept open
    max_overflow=10,      # extra connections allowed above pool_size under load
    pool_recycle=3600,    # recycle connections after 1 hour
    pool_timeout=30,      # seconds to wait for a free connection before raising
)