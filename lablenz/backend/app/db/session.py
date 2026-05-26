from sqlmodel import Session
from .database import engine


def get_session():
    """
    Dependency function that provides a database session to FastAPI routes.

    Automatically commits on success and rolls back on any exception.
    Session is always closed after the request completes.

    Usage:
        @router.get("/items")
        def get_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise