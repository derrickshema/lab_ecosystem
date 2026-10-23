# Identity

Consolidated authentication for every app in the ecosystem. Owns users, facilities, and staff access grants (which role a user holds at which facility). Issues RS256-signed JWTs that EHR, LabLenz and the other apps verify with the public key.

| | |
|---|---|
| API (Docker) | http://localhost:8002 (docs at `/docs`) |
| On `lab_net` | `http://identity:8000` |
| Public keys | `GET /.well-known/jwks.json` |
| Database | `identity_db` on the shared server |

## First-time setup

From `apps/identity/backend/` with the `.venv` activated (shared infrastructure running):

```sh
cp .env.example .env                  # then set SUPERADMIN_PASSWORD
python -m scripts.generate_jwt_keys   # writes keys/ (gitignored, never commit)
alembic upgrade head
python -m scripts.create_superadmin
```

Then `docker compose up -d` from `apps/identity/`.

## How tokens work

```
Identity                          EHR / LabLenz
  private key ── signs ──► JWT ──► verified with public key (from JWKS)
```

Only Identity holds the private key, so only Identity can create tokens. Apps holding the public key can verify tokens but never forge them.

Access token claims: `sub` (user ID), `username`, `role` (system role), `org_role` and `facility_id` (the facility chosen at login; null for a super admin's platform-wide session), plus `iss`, `iat`, `exp`, `jti`, `token_type`.

## Login flow

1. `POST /auth/login`. With one active facility assignment you get tokens. With several, you get a facility picker and a 5-minute `selection_token`. With none, you get 403, except a super admin, who gets a platform-wide session.
2. `POST /auth/facility-select` with the `selection_token` and chosen `facility_id` gives you tokens.
3. `POST /auth/refresh` keeps the same facility, as long as that access is still active.

## Bootstrapping a facility (super admin)

1. `POST /facilities` creates the facility.
2. `POST /users/` creates a staff user, optionally with `org_role` and `facility_id`.
3. `POST /facilities/{id}/staff` grants an existing user a role. `DELETE .../staff/{assignment_id}` revokes it. Grants are deactivated, never deleted, so the audit trail is kept.

## Rotating the signing key

`python -m scripts.generate_jwt_keys --force`, then change `JWT_KEY_ID`. Existing tokens stop verifying, so everyone logs in again.
