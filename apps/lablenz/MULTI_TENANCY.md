# Multi-Tenancy Patterns

> Living document — built from real implementation. Add to this as new patterns are established.

---

## Model: Identity vs. Access Grant

The core principle: **user identity is global; tenant/organisation access is a scoped grant**.

```
User (global identity)
  │
  └── UserMembership / UserFacility (access grant per tenant)
        ├── tenant_id    → Tenant / Facility
        ├── org_role     (MANAGER, MEMBER, etc. — project-specific)
        ├── is_active
        └── assigned_at / deactivated_at
```

A single `User` row can have many access grant rows — one per tenant/organisation they belong to, potentially with different roles at each.

### Why separate User from the access grant table?

| Concern | Decision | Rationale |
|---|---|---|
| User deactivation | Deactivate the access grant row, never delete `User` | Preserves audit trail — who did what, when |
| Role at a tenant | Stored on access grant, not `User` | Same person can be MANAGER at org A and MEMBER at org B |
| Multiple roles at same tenant | UniqueConstraint on `(user_id, tenant_id, org_role)` allows it | e.g. two different roles at the same organisation |
| JWT tenant context | Set at login from chosen access grant row | Stateless per-request enforcement without joins |

---

## Tenant Model (e.g. `Facility`, `Organisation`, `Workspace`)

```python
# Example: Lablenz Facility
class Facility(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, index=True)
    code: str | None = Field(default=None, max_length=50, unique=True)   # e.g. "MGH", "BWH"
    address: str | None = Field(default=None, max_length=500)
    created_at: datetime  # timezone-aware
    updated_at: datetime  # timezone-aware
```

---

## Access Grant Model (e.g. `UserFacility`, `UserMembership`, `UserOrganisation`)

```python
# Example: Lablenz UserFacility
class UserFacility(SQLModel, table=True):
    __tablename__ = "user_facility"
    __table_args__ = (
        UniqueConstraint("user_id", "facility_id", "org_role", name="uq_user_facility_role"),
    )
    id: int | None
    user_id: int       # FK → user.id
    facility_id: int   # FK → facility.id (the tenant)
    org_role: OrgRole  # sa_column with SAEnum
    is_active: bool = True
    assigned_at: datetime
    deactivated_at: datetime | None = None
```

### Deactivating access (never deleting)
```python
# On resignation / role removal:
uf.is_active = False
uf.deactivated_at = datetime.now(timezone.utc)
session.commit()
# User row is untouched — historical data remains attributable
```

---

## Login Flow (EPIC-inspired)

Inspired by how EPIC handles department/facility context selection at login. Applies to any system where a user can belong to multiple tenants/organisations with different roles.

```
POST /auth/login
     │
     ├── verify credentials
     │
     ├── query active access grant assignments
     │
     ├── 0 assignments ──→ 403 "No active tenant assignments"
     │
     ├── 1 assignment  ──→ issue access + refresh tokens immediately
     │                     (auto-select, transparent to user)
     │
     └── 2+ assignments ─→ TenantSelectionRequired response
                             {
                               selection_required: true,
                               tenants: [{tenant_id, tenant_name, org_role}, ...],
                               selection_token: "<5-min JWT>"
                             }
                                    │
                                    ↓
                           POST /auth/tenant-select
                             { tenant_id: N, selection_token: "..." }
                                    │
                                    ↓
                           validate token + check assignment is still active
                                    │
                                    ↓
                           issue access + refresh tokens
```

### Why a selection_token?
The facility selection step needs to be tied to a specific authenticated user without issuing a full access token. A short-lived JWT (`token_type: facility_selection`, 5 min TTL) carries only `user_id`. The client sends it back with their chosen `facility_id`; the server verifies ownership and issues full tokens.

This prevents:
- Unauthenticated facility selection requests
- One user selecting a facility on behalf of another

---

## JWT Tenant Context

Every access token carries the tenant context selected at login:

```python
# Example: Lablenz
token_payload = {
    "sub": str(user.id),
    "user_id": user.id,
    "username": user.username,
    "role": user.role.value,        # SystemRole — global
    "org_role": uf.org_role.value,  # OrgRole — for this session
    "facility_id": uf.facility_id,  # which tenant this session is scoped to
}
```

`token_data.tenant_id` / `token_data.facility_id` is then available in every route handler via `get_token_data` — no join needed to scope queries:

```python
# Scope a query to the current tenant automatically
results = session.exec(
    select(Record).where(Record.facility_id == token_data.facility_id)  # e.g. LabResult in Lablenz
).all()
```

---

## Token Transport

Tokens are set as **httpOnly cookies** in addition to being returned in the JSON body. This allows both SPA (reads from JSON) and server-side rendering (reads from cookie) to work without any client-side adaptation.

```python
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,           # JS cannot read — prevents XSS token theft
    secure=not settings.DEBUG,   # HTTPS only in production
    samesite="lax",          # CSRF protection on cross-site navigations
    max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
)
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=not settings.DEBUG,
    samesite="lax",
    max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    path="/auth/refresh",    # cookie only sent to the refresh endpoint
)
```

`path="/auth/refresh"` on the refresh cookie ensures the browser only sends it to that one endpoint — reduces the attack surface.

---

## Token Lookup Priority

```python
COOKIE_NAME = "access_token"

async def get_token_from_cookie_or_header(
    cookie_token: str | None = Cookie(default=None, alias=COOKIE_NAME),
    bearer_token: str | None = Depends(oauth2_scheme),
) -> str:
    token = cookie_token or bearer_token
    if not token:
        raise HTTPException(401, "Not authenticated")
    return token
```

Cookie takes priority over `Authorization: Bearer` header. This is correct: cookies are set by the server; a header could be spoofed by JS if XSS occurs. Both paths work, allowing API clients (curl, Postman) to use Bearer headers.

---

## Refresh Token Strategy

The refresh token **does not carry tenant context** — it only carries `user_id`. On refresh:
1. Validate the refresh token
2. Re-query access grant table for active assignments
3. If 1 assignment → issue new tokens
4. If 0 or 2+ → fail gracefully (force re-login to re-select context)

This means a user whose tenant assignment changed mid-session will be caught at the next refresh, not at the next access token expiry.

---

## Deployment Model

Single backend deployment serves all tenants. Tenants are rows in the tenant table, not separate deployments. This matches how EPIC and Cerner are deployed within a health network, or how a SaaS product serves multiple organisations from one instance.

This is different from infrastructure-level multi-tenancy where each tenant gets isolated infrastructure. Here:
- All data is in the same PostgreSQL instance
- Tenant isolation is enforced at the application layer via `tenant_id` / `facility_id` column filters
- A `SUPER_ADMIN` has cross-tenant visibility; regular users are scoped to their JWT tenant context

---

## Secondary User Type (Future)

Some applications have a second class of user with a fundamentally different access model (e.g. customers, patients, end-users). Their auth is deliberately separate:

| Concern | Staff / Members | Secondary Users (e.g. patients, customers) |
|---|---|---|
| Model | `User` + access grant table | Separate table (e.g. `Patient`, `Customer`) |
| Auth dependency | `dependencies/auth.py` | `dependencies/secondary_auth.py` (future) |
| JWT tenant context | Yes — scoped to logged-in tenant | No — sees all their own data across all tenants |
| OrgRole | Yes | No |
| SystemRole | Yes | No |

Domain records carry both `secondary_user_id` and `tenant_id` FKs so both query patterns work: a staff member sees records for their tenant; a secondary user sees all their own records everywhere.

Never add secondary user types to `OrgRole` — they are not staff/members and the role systems must stay separate.

---

## Patterns to Avoid

- Putting `org_role` or `tenant_id` on the `User` table — breaks the identity/access separation
- Deleting `User` on departure — loses audit trail; deactivate the access grant row instead
- Hardcoding `tenant_id` in queries — always read from `token_data`
- Single `tenant_id` FK on `User` — prevents multi-tenant assignments; use a separate access grant table
- Adding secondary user types (customers, patients) to `OrgRole` — they use a separate model and auth chain
