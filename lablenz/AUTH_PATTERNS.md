# FastAPI Authentication Patterns

> Living document — built from real implementation. Add to this as new patterns are established.

---

## Stack
- **FastAPI** + **SQLModel** + **Pydantic v2** + **PostgreSQL**
- JWT-based auth (access + refresh tokens)
- RBAC (system role + org role)

---

## User Schema Architecture

### Base class rule
| Schema type | Base class | Why |
|---|---|---|
| DB table model | `SQLModel` (`table=True`) | ORM + Pydantic combined |
| Shared field base | `SQLModel` (no `table=True`) | Inherited by table model |
| All other schemas | `BaseModel` | Pure Pydantic, no DB overhead |

**Never use `SQLModel` as base for request/response schemas.** `index=True`, `unique=True`, and `sa_column` are SQLAlchemy directives — meaningless and potentially harmful on non-table models.

### Schema inventory (what to always have)

| Class | Purpose | Base |
|---|---|---|
| `UserBase` | Shared fields (name, username, email, role) | `SQLModel` |
| `User` | ORM table model — source of truth | `UserBase` + `table=True` |
| `UserCreate` | Registration input | `UserBase` |
| `UserRead` | API response — safe, no password | `UserBase` |
| `UserUpdate` | Profile update (all fields optional) | `BaseModel` |
| `UserPasswordChange` | Change password (requires old password) | `BaseModel` |
| `UserLogin` | Login request body (JSON) | `BaseModel` |
| `Token` | Token response | `BaseModel` |
| `TokenData` | Decoded JWT payload (internal use) | `BaseModel` |
| `RefreshToken` | Refresh token request body | `BaseModel` |
| `UserPasswordReset` | Forgot password — step 1 (email) | `BaseModel` |
| `UserPasswordResetConfirm` | Forgot password — step 2 (token + new password) | `BaseModel` |
| `UserEmailVerification` | Resend verification email request | `BaseModel` |
| `UserEmailVerificationConfirm` | Confirm email with token | `BaseModel` |

### UserInDB — skip with SQLModel
`UserInDB` is a pre-SQLModel FastAPI pattern for raw SQLAlchemy + Pydantic stacks, where ORM models had no Pydantic capabilities. With SQLModel, `User` already serves this purpose. Don't add it.

---

## Password Validation

### Rule: enforce policy only where password is SET, never where it is CHECKED

| Operation | Enforce complexity? | Enforce min_length? |
|---|---|---|
| `UserCreate` | Yes | Yes |
| `UserUpdate` (password field) | Yes | Yes |
| `UserPasswordChange.new_password` | Yes | Yes |
| `UserPasswordResetConfirm.new_password` | Yes | Yes |
| `UserLogin.password` | No | No — `max_length` only (DoS guard) |
| `UserPasswordChange.old_password` | No | No — `max_length` only |

### Validator redundancy
`Field(min_length=8)` already rejects short passwords before the validator runs. Do **not** add `if len(value) < 8` inside `@field_validator` — it is dead code.

### Complexity checks (standard set)
```python
if not re.search(r"[A-Z]", value): ...   # uppercase
if not re.search(r"[a-z]", value): ...   # lowercase
if not re.search(r"[0-9]", value): ...   # digit
if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value): ...  # special char
```

---

## Email Validation

`EmailStr` from Pydantic already validates format. Do **not** add a redundant regex inside `validate_email`. The validator only needs to normalise:
```python
@field_validator("email")
def validate_email(cls, value: str) -> str:
    return value.lower()
```

---

## Timestamps

### Always use timezone-aware datetimes
```python
from datetime import datetime, timezone
from sqlalchemy import DateTime, func

created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now()
    )
)
updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    sa_column=Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc)
    )
)
```

**Key points:**
- `DateTime(timezone=True)` — stores timezone-aware datetimes in DB (TIMESTAMPTZ in PostgreSQL)
- `default_factory` — Python-side default (used before DB commit)
- `server_default=func.now()` — DB-side fallback
- `onupdate` — auto-updates `updated_at` on every UPDATE
- Use `datetime.now(timezone.utc)` not `datetime.utcnow()` — deprecated in Python 3.12+
- Type as `datetime` not `str` in both the ORM model and response schemas

---

## Token Design

### Token response
```python
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None   # for token rotation
    expires_in: int                     # seconds until expiry
```

### TokenData (decoded JWT payload — internal only)
```python
class TokenData(BaseModel):
    user_id: int          # required — avoids DB lookup on every request
    username: str | None = None
    role: SystemRole | None = None
    org_role: OrgRole | None = None
    facility_id: int | None = None
```

**`user_id` must be required** — making it optional forces `None` handling throughout the auth dependency.

---

## Login Flow Options

### Option A: JSON body (natural for SPAs / SvelteKit)
```python
class UserLogin(BaseModel):
    username: str = Field(max_length=50)
    password: str = Field(max_length=255)  # max only, not min

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, session: Session = Depends(get_session)):
    ...
```

### Option B: OAuth2 form data (FastAPI standard, Swagger UI integration)
```python
from fastapi.security import OAuth2PasswordRequestForm

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # form_data.username, form_data.password
```
No `UserLogin` class needed. Gives free Swagger "Authorize" button.

---

## RBAC Notes
- `SystemRole` — global system-level role (e.g., SUPERADMIN, ADMIN, USER)
- `OrgRole` — role within an organisation/facility context
- Both stored in JWT via `TokenData` to avoid DB lookups per request
- `facility_id` in token enables scoped data access without extra queries

---

## Patterns to Avoid
- `UserInDB` with SQLModel — redundant, use `User` directly
- `sa_column` / `index=True` / `unique=True` on non-table schemas — silently ignored or causes errors
- `min_length` on login password fields — can lock out valid users
- `str` type for timestamps — use `datetime` with `DateTime(timezone=True)`
- `datetime.utcnow()` — deprecated since Python 3.12, use `datetime.now(timezone.utc)`
- Redundant length checks inside validators when `Field(min_length=...)` already covers it
- Redundant email regex when `EmailStr` already validates format
