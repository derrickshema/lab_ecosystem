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

## JWT (`security/jwt.py`)

### Library: PyJWT (not python-jose)
`python-jose` has active CVEs (CVE-2024-33664, CVE-2024-33663 — algorithm confusion attacks) and is barely maintained since 2022. Use `PyJWT`:
```python
import jwt
from jwt import InvalidTokenError  # catches all decode failures
```

### Every token must carry these claims
| Claim | Purpose |
|---|---|
| `exp` | Expiry — required |
| `iat` | Issued-at — useful for audit logs and "issued after logout" checks |
| `jti` | Unique UUID — enables individual token revocation/blacklisting |
| `token_type` | `"access"`, `"refresh"`, or `"password_reset"` — prevents cross-type abuse |

```python
import uuid
to_encode.update({
    "exp": expire,
    "iat": datetime.now(timezone.utc),
    "jti": str(uuid.uuid4()),
    "token_type": "access",  # or "refresh" / "password_reset"
})
```

### Always validate token_type on decode
```python
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
if payload.get("token_type") != "access":
    raise HTTPException(401, "Invalid token type", headers={"WWW-Authenticate": "Bearer"})
```
This prevents a refresh token being submitted where an access token is expected and vice versa.

### Function inventory
```python
create_access_token(data, expires_delta=None) -> str
decode_access_token(token) -> dict          # raises HTTPException on failure

create_refresh_token(data, expires_delta=None) -> str
decode_refresh_token(token) -> dict         # raises HTTPException on failure

create_password_reset_token(email) -> str
verify_password_reset_token(token) -> str | None  # returns None on failure (not exception)
```

`decode_*` raises `HTTPException` — used in protected endpoints.
`verify_password_reset_token` returns `None` — used in the reset route where you control the error response.

### Exception handling
`InvalidTokenError` catches the full PyJWT hierarchy: expired, invalid signature, malformed, wrong algorithm — everything needed in one except clause.

### All expiry settings belong in config
```python
# config.py
ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
```
Never hardcode expiry values in `jwt.py`.

### jti and token revocation
With `jti` on every token you can implement a denylist (Redis or DB table) to invalidate individual tokens on logout or after a password change — without rotating the secret key. Without `jti`, the only way to invalidate a token is to rotate `SECRET_KEY`, which logs out every user.

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

## Password Hashing (`security/passwords.py`)

### Algorithm: Argon2id (not bcrypt)
Argon2id is OWASP's first-choice algorithm (winner of Password Hashing Competition 2015). bcrypt is still acceptable but second-best.

```python
# pip install argon2-cffi
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",        # string, NOT ["auto"] — list form is incorrect API usage
    argon2__time_cost=3,       # iterations
    argon2__memory_cost=65536, # 64 MiB — OWASP recommended
    argon2__parallelism=4,
)
```

### Three functions — cover all use cases
```python
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def needs_rehash(hashed_password: str) -> bool:
    """True if hash was created with weaker parameters than current config."""
    return pwd_context.needs_update(hashed_password)
```

### Silent rehash on login (use needs_rehash)
The only moment you have the plain password is during login. Use it to silently upgrade stale hashes:
```python
if needs_rehash(user.hashed_password):
    user.hashed_password = hash_password(credentials.password)
    session.add(user)
    session.commit()
```
This ensures all active users are gradually upgraded whenever work factors are increased — transparent to the user.

### Argon2 OWASP parameters
- `time_cost=3` — iterations (minimum 1, recommended ≥2)
- `memory_cost=65536` — 64 MiB (OWASP recommended; minimum is 19456 / 19 MiB)
- `parallelism=4` — parallel threads
- If server is memory-constrained, use `memory_cost=19456, time_cost=2, parallelism=1` as minimum

### passlib note
passlib has had limited maintenance since ~2021. It still works correctly. Monitor for updates; `argon2-cffi` directly is an alternative if passlib is ever abandoned.

---

## Patterns to Avoid
- `UserInDB` with SQLModel — redundant, use `User` directly
- `sa_column` / `index=True` / `unique=True` on non-table schemas — silently ignored or causes errors
- `min_length` on login password fields — can lock out valid users
- `str` type for timestamps — use `datetime` with `DateTime(timezone=True)`
- `datetime.utcnow()` — deprecated since Python 3.12, use `datetime.now(timezone.utc)`
- Redundant length checks inside validators when `Field(min_length=...)` already covers it
- Redundant email regex when `EmailStr` already validates format
