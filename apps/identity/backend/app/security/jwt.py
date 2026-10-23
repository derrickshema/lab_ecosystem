"""
JWT creation and verification (RS256).

Identity signs every token with its PRIVATE key. Anyone with the PUBLIC key
can verify a token, but only Identity can create one. Other apps fetch the
public key from GET /.well-known/jwks.json.

Every token carries:
  iss         — JWT_ISSUER; verifiers reject other issuers
  iat / exp   — issued-at / expiry
  jti         — unique token ID (for future revocation)
  token_type  — access | refresh | password_reset | email_verification |
                facility_selection. Decoders check it, so e.g. a refresh token
                can never be used as an access token.
and a `kid` header naming the key that signed it.
"""

import uuid
from datetime import datetime, timedelta, timezone
from functools import cache
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi import HTTPException, status
from jwt import InvalidTokenError
from jwt.algorithms import RSAAlgorithm

from ..config import settings


# --- Keys ---

@cache
def _private_key() -> str:
    return Path(settings.JWT_PRIVATE_KEY_PATH).read_text()


@cache
def _public_key() -> str:
    return Path(settings.JWT_PUBLIC_KEY_PATH).read_text()


def public_jwks() -> dict:
    """The public key as a JSON Web Key Set, served at /.well-known/jwks.json."""
    jwk = RSAAlgorithm.to_jwk(load_pem_public_key(_public_key().encode()), as_dict=True)
    jwk.update({"kid": settings.JWT_KEY_ID, "use": "sig", "alg": settings.ALGORITHM})
    return {"keys": [jwk]}


# --- Generic encode/decode ---

def _encode(claims: dict, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        **claims,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
        "token_type": token_type,
    }
    return jwt.encode(
        to_encode,
        _private_key(),
        algorithm=settings.ALGORITHM,
        headers={"kid": settings.JWT_KEY_ID},
    )


def _decode(token: str, token_type: str) -> dict | None:
    """Return the payload if the token is valid and of the expected type, else None."""
    try:
        payload = jwt.decode(
            token,
            _public_key(),
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except InvalidTokenError:
        return None
    if payload.get("token_type") != token_type:
        return None
    return payload


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


# --- Access Tokens ---

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    return _encode(data, "access", expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def decode_access_token(token: str) -> dict:
    """Verify a JWT access token and return the payload."""
    payload = _decode(token, "access")
    if payload is None:
        raise _unauthorized("Could not validate credentials")
    return payload


# --- Refresh Tokens ---

def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token."""
    return _encode(data, "refresh", expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))


def decode_refresh_token(token: str) -> dict:
    """Verify a JWT refresh token and return the payload."""
    payload = _decode(token, "refresh")
    if payload is None:
        raise _unauthorized("Could not validate credentials")
    return payload


# --- Password Reset Tokens ---

def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT token for password reset."""
    return _encode({"sub": email}, "password_reset", timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES))


def verify_password_reset_token(token: str) -> str | None:
    """Verify a password reset token and return the email, or None if invalid."""
    payload = _decode(token, "password_reset")
    return payload.get("sub") if payload else None


# --- Facility Selection Tokens ---

def create_facility_selection_token(user_id: uuid.UUID) -> str:
    """
    Short-lived (5 min) token for multi-facility users.
    Carries only user_id; the client POSTs it back with the chosen facility_id.
    """
    return _encode({"sub": str(user_id)}, "facility_selection", timedelta(minutes=5))


def decode_facility_selection_token(token: str) -> uuid.UUID:
    """Verify a facility selection token and return the user_id."""
    payload = _decode(token, "facility_selection")
    try:
        return uuid.UUID(payload["sub"])  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired selection token")


# --- Email Verification Tokens ---

def create_email_verification_token(email: str) -> str:
    """Create a short-lived JWT token for email address verification."""
    return _encode({"sub": email}, "email_verification", timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES))


def verify_email_verification_token(token: str) -> str | None:
    """Verify an email verification token and return the email, or None if invalid."""
    payload = _decode(token, "email_verification")
    return payload.get("sub") if payload else None
