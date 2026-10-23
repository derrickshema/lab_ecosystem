"""
Verify Identity's access tokens in any app — no shared secret, no database.

Identity signs tokens with its private key and publishes the public key at
/.well-known/jwks.json. Apps fetch that once (it's cached) and verify every
request locally, so Identity isn't called per request.

Usage (in an app's app/auth.py):

    from labcore.auth import Auth
    from .config import settings

    auth = Auth(jwks_url=settings.IDENTITY_JWKS_URL, issuer=settings.IDENTITY_ISSUER)

In routes:

    from labcore.auth import AccessClaims
    from labcore.roles import OrgRole

    @router.post("/patients")
    def register(claims: AccessClaims = Depends(auth.require_org_role(OrgRole.REGISTRATION_PERSONNEL))):
        claims.user_id, claims.facility_id   # who, and at which facility
"""

import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError
from pydantic import BaseModel

from .roles import OrgRole, SystemRole


class AccessClaims(BaseModel):
    """The verified contents of an access token."""
    user_id: uuid.UUID
    username: str | None
    role: SystemRole
    # The facility chosen at login, and the user's role there. Both are None
    # for a super admin's platform-wide session.
    org_role: OrgRole | None
    facility_id: uuid.UUID | None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


class Auth:
    """
    Token verification plus FastAPI dependencies, configured once per app.

    Tokens are read from the `access_token` httpOnly cookie (set by Identity
    at login, for browser/SSR requests) or the Authorization: Bearer header
    (API clients, Swagger's Authorize button).
    """

    def __init__(
        self,
        jwks_url: str,
        issuer: str = "lab-identity",
        cookie_name: str = "access_token",
        algorithms: tuple[str, ...] = ("RS256",),
    ):
        # Caches the fetched keys; refetches when a token names an unknown kid
        # (i.e. after Identity rotates its key).
        self._jwks = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        self._issuer = issuer
        self._cookie_name = cookie_name
        self._algorithms = list(algorithms)
        bearer = HTTPBearer(auto_error=False)

        def current_claims(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
        ) -> AccessClaims:
            token = request.cookies.get(self._cookie_name) or (credentials.credentials if credentials else None)
            if not token:
                raise _unauthorized("Not authenticated")
            return self.verify(token)

        self.current_claims: Callable[..., AccessClaims] = current_claims

    def verify(self, token: str) -> AccessClaims:
        """Check signature, issuer, expiry and token type; return the claims or raise 401."""
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token,
                key,
                algorithms=self._algorithms,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "iss", "sub"]},
            )
        except PyJWKClientError:
            # Unknown kid, or Identity unreachable when keys weren't cached yet
            raise _unauthorized("Could not validate credentials")
        except InvalidTokenError:
            raise _unauthorized("Could not validate credentials")

        # A refresh/reset/verification token must never work as an access token
        if payload.get("token_type") != "access":
            raise _unauthorized("Invalid token type")
        try:
            return AccessClaims(
                user_id=payload["sub"],
                username=payload.get("username"),
                role=payload.get("role"),
                org_role=payload.get("org_role"),
                facility_id=payload.get("facility_id"),
            )
        except ValueError:
            raise _unauthorized("Invalid authentication token")

    def require_org_role(self, *roles: OrgRole) -> Callable[..., AccessClaims]:
        """
        Dependency factory: the session's role at its facility must be one of `roles`.
        Implies a facility context, so a super admin's platform session never passes.

            @router.post("/visits/{id}/assign", dependencies=[Depends(auth.require_org_role(OrgRole.CLINICAL_MANAGER))])
        """
        def guard(claims: AccessClaims = Depends(self.current_claims)) -> AccessClaims:
            if claims.facility_id is None or claims.org_role not in roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            return claims
        return guard

    def require_system_role(self, *roles: SystemRole) -> Callable[..., AccessClaims]:
        """Dependency factory: the user's platform-wide role must be one of `roles`."""
        def guard(claims: AccessClaims = Depends(self.current_claims)) -> AccessClaims:
            if claims.role not in roles:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
            return claims
        return guard
