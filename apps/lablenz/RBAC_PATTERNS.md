# RBAC / Authorization Patterns

> Living document — built from real implementation. Add to this as new patterns are established.

---

## Concept: Two Role Layers

This pattern uses two orthogonal role systems that coexist in every JWT:

| Layer | Enum | Stored on | Scope | Example values |
|---|---|---|---|---|
| **SystemRole** | `SystemRole` | `User.role` (DB column) | Global — applies everywhere | `SUPER_ADMIN`, `USER` |
| **OrgRole** | `OrgRole` | access grant table + JWT claim (e.g. `UserFacility.org_role`) | Tenant/org-scoped — per login context | `LAB_TECHNICIAN`, `PROVIDER`, `MANAGER`, `MEMBER` |

- `SystemRole` answers: *is this person allowed to operate the platform at all, and with what admin level?*
- `OrgRole` answers: *what organisation role does this person hold in the tenant/context they are currently logged into?*

Users with a different access pattern (e.g. customers, patients) are **not** modelled as either role. They use a separate auth/data model.

---

## Auth Dependency Chain

```
get_token_from_cookie_or_header
        ↓
get_token_data(token)            ← JWT decoded ONCE; FastAPI caches result per request
     ↙           ↘
get_current_user   require_org_role._guard   (reads token_data.org_role — no extra DB query)
(DB lookup)
     ↓
get_verified_user  (checks email_verified)
```

**Key insight:** `get_token_data` is a regular FastAPI dependency. When multiple guards (`get_current_user` + `require_org_role`) both depend on it, FastAPI resolves it once and injects the cached result into both. The JWT is never decoded more than once per request.

---

## SystemRole Guard (`require_system_role`)

Checks `current_user.role` from the database row — authoritative, always fresh.

```python
def require_system_role(*roles: SystemRole):
    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _guard
```

### Usage
```python
# As a route dependency (no user object needed in handler)
@router.delete("/facilities/{id}", dependencies=[Depends(require_system_role(SystemRole.SUPER_ADMIN))])

# As a typed dependency (user object needed in handler)
@router.post("/users/")
async def create_user(admin: User = Depends(require_system_role(SystemRole.SUPER_ADMIN))):
    ...
```

---

## OrgRole Guard (`require_org_role`)

Checks `token_data.org_role` from the **JWT** — stateless, no DB query.

```python
def require_org_role(*roles: OrgRole):
    async def _guard(
        current_user: User = Depends(get_current_user),
        token_data: TokenData = Depends(get_token_data),
    ) -> User:
        if token_data.org_role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return _guard
```

### Why read from JWT, not DB?
`org_role` lives on the access grant table (e.g. `UserFacility`), not on `User`. Reading it from the DB on every request would require a join. The JWT carries the role from the access grant row selected at login — it's a snapshot, valid for the life of the access token (30 min default).

### High-sensitivity endpoints
For operations where stale role data is unacceptable, additionally verify the access grant's `is_active` flag directly in the route handler:
```python
# Example (Lablenz): approving a critical lab result
@router.post("/results/{id}/approve")
async def approve_result(
    id: int,
    token_data: TokenData = Depends(get_token_data),
    current_user: User = Depends(require_org_role(OrgRole.PROVIDER)),
    session: Session = Depends(get_session),
):
    # Belt-and-suspenders: verify access grant hasn't been revoked since token was issued
    uf = session.exec(
        select(UserFacility).where(
            UserFacility.user_id == current_user.id,
            UserFacility.facility_id == token_data.facility_id,
            UserFacility.is_active == True,
        )
    ).first()
    if not uf:
        raise HTTPException(status_code=403, detail="Organisation access has been revoked")
    ...
```

### Usage
```python
# Single role
@router.post("/samples/", dependencies=[Depends(require_org_role(OrgRole.LAB_TECHNICIAN))])

# Multiple allowed roles
@router.get("/results/", dependencies=[Depends(require_org_role(
    OrgRole.LAB_TECHNICIAN, OrgRole.PROVIDER
))])
```

---

## Convenience Dependencies

Pre-built for the most common cases — use these directly in route signatures:

```python
# SUPER_ADMIN check only
async def get_superadmin(current_user: User = Depends(get_current_user)) -> User

# SUPER_ADMIN + email verified
async def get_verified_superadmin(current_user: User = Depends(get_verified_user)) -> User
```

```python
# Usage
@router.post("/admin/reset-db")
async def nuke(admin: User = Depends(get_verified_superadmin)):
    ...
```

---

## Email Verification Guard (`get_verified_user`)

Some sensitive operations (profile changes, tenant access) require a verified email. Use `get_verified_user` instead of `get_current_user`:

```python
async def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.email_verified:
        raise HTTPException(status_code=403, detail="Email address not verified")
    return current_user
```

Apply to routes that touch PII or grant access downstream.

---

## Combining Guards

Guards compose naturally via FastAPI's dependency injection:

```python
# Require: valid token + verified email + PROVIDER org role
@router.post("/orders/")
async def create_order(
    current_user: User = Depends(require_org_role(OrgRole.PROVIDER)),
    token_data: TokenData = Depends(get_token_data),
    session: Session = Depends(get_session),
):
    # current_user is guaranteed: authenticated + PROVIDER role in token
    # token_data.facility_id is the scoped facility context
    ...
```

---

## What RBAC Does NOT Cover

- **Row-level security** (e.g., can this member access this resource?) — enforce in route handlers by filtering on `tenant_id`/`facility_id` from `token_data`
- **Secondary user type access** (e.g. customers, patients) — these users have a separate auth chain (no `OrgRole`, no `tenant_id` in token); handled by a dedicated auth dependency
- **Token revocation** — `jti` claim exists on all tokens; a Redis/DB denylist can be added to `get_token_data` without changing any route code

---

## Patterns to Avoid

- `hasattr(current_user, "org_role")` — `User` ORM has no `org_role` field (it's on the access grant table, e.g. `UserFacility`); always read from `token_data`
- Checking `User.role` for OrgRole enforcement — they're different axes; don't conflate them
- Adding `role` field to `UserUpdate` — role changes are a privileged admin operation, not self-service
- Overriding `role` in `UserCreate` — locked to `Literal[SystemRole.USER]` to prevent privilege escalation at registration
