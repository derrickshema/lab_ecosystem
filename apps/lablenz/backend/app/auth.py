"""Verifies access tokens issued by apps/identity, using labcore's shared Auth."""

from labcore.auth import Auth

from .config import settings

auth = Auth(jwks_url=settings.IDENTITY_JWKS_URL, issuer=settings.IDENTITY_ISSUER)
