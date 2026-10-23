"""Database engine and session for this app, built from the shared labcore helpers."""

from labcore.db import make_engine, make_session_dependency

from .config import settings

engine = make_engine(settings.DATABASE_URL, echo=settings.DEBUG)
get_session = make_session_dependency(engine)
