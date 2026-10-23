"""
Database engine and session helpers shared by every app.

Each app owns its own settings, so these are factories: the app passes in its
DATABASE_URL and gets back an engine and a FastAPI session dependency.

Usage (in an app's app/db.py):

    from labcore.db import make_engine, make_session_dependency
    from .config import settings

    engine = make_engine(settings.DATABASE_URL, echo=settings.DEBUG)
    get_session = make_session_dependency(engine)
"""

from collections.abc import Callable, Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine


def make_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create the connection pool for one database. Call once per app, at import time."""
    return create_engine(
        database_url,
        echo=echo,
        pool_pre_ping=True,   # test connections before use — prevents stale connection errors
        pool_size=5,          # persistent connections kept open
        max_overflow=10,      # extra connections allowed above pool_size under load
        pool_recycle=3600,    # recycle connections after 1 hour
        pool_timeout=30,      # seconds to wait for a free connection before raising
    )


def make_session_dependency(engine: Engine) -> Callable[[], Iterator[Session]]:
    """
    Build a FastAPI dependency that provides a session bound to `engine`.

    Automatically commits on success and rolls back on any exception.
    Session is always closed after the request completes.

        @router.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()
    """
    def get_session() -> Iterator[Session]:
        with Session(engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    return get_session
