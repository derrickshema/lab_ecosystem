# FastAPI Persistence Patterns

> Living document — built from real implementation. Add to this as new patterns are established.

---

## Stack
- **SQLModel** + **SQLAlchemy** + **PostgreSQL**
- **Alembic** for migrations
- Session-per-request pattern via FastAPI dependency injection

---

## Where this code lives

The engine and session code is shared by every app in `packages/labcore/labcore/db.py`. Each app wires it up in a 3-line `app/db.py`:

```python
from labcore.db import make_engine, make_session_dependency
from .config import settings

engine = make_engine(settings.DATABASE_URL, echo=settings.DEBUG)
get_session = make_session_dependency(engine)
```

The snippets below show what `labcore` does inside.

---

## Engine Configuration (`labcore.db.make_engine`)

### Always configure the connection pool explicitly
```python
from sqlmodel import create_engine

engine = create_engine(
    database_url,
    echo=echo,
    pool_pre_ping=True,   # test connections before use — prevents stale connection errors
    pool_size=5,          # persistent connections kept open
    max_overflow=10,      # extra connections allowed above pool_size under load
    pool_recycle=3600,    # recycle connections after 1 hour
    pool_timeout=30,      # seconds to wait for a free connection before raising
)
```

### `pool_pre_ping=True` — most critical setting
Without this, stale connections from the pool (after a DB restart, cloud DB timeout, or Docker restart) cause `OperationalError` on the next request. `pool_pre_ping` issues a lightweight `SELECT 1` before each connection use to detect and discard dead connections.

**Always set this in production.**

### Pool settings guide
| Setting | Default | Recommended | Notes |
|---|---|---|---|
| `pool_pre_ping` | `False` | `True` | Critical — prevents stale connection errors |
| `pool_size` | `5` | `5` | Persistent connections — tune to workload |
| `max_overflow` | `10` | `10` | Burst capacity above `pool_size` |
| `pool_recycle` | `-1` (never) | `3600` | Recycle after 1h — prevents long-lived stale connections |
| `pool_timeout` | `30` | `30` | Seconds to wait for a free connection |

---

## Session Management (`labcore.db.make_session_dependency`)

### Auto-commit pattern (recommended)
```python
from sqlmodel import Session

def get_session():  # built per app, bound to that app's engine
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

**How it works:**
- Request comes in → session created
- Route handler runs — adds/updates/deletes objects
- Route returns without error → `session.commit()` fires automatically
- Route raises an exception → `session.rollback()` fires, exception re-raised
- Session always closed by the `with` block

**Benefit:** Routes don't need to call `session.commit()` manually — cleaner route handlers.

### Alternative: explicit commit per route
```python
def get_session():
    with Session(engine) as session:
        yield session
        # routes must call session.commit() themselves
```
Gives finer control but adds boilerplate to every write route. Prefer the auto-commit pattern.

### Injecting the session in routes
```python
from fastapi import Depends
from sqlmodel import Session, select
from app.db import get_session

@router.get("/items")
def get_items(session: Session = Depends(get_session)):
    return session.exec(select(Item)).all()
```

---

## Patterns to Avoid
- Omitting `pool_pre_ping=True` — causes mysterious `OperationalError` crashes after DB restarts
- Leaving pool settings as defaults — invisible in code, hard to tune later
- Creating a new engine per request — extremely expensive, defeats connection pooling
- Calling `session.commit()` in routes when using the auto-commit pattern — double commit is harmless but redundant
