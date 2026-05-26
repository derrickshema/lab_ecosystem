"""
Authentication Module

This module handles user authentication - determining WHO the user is.
It extracts and validates JWT tokens from cookies or headers.
"""

from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session

from ..db.session import get_session
from ..models.user import TokenData, User
from ..security.jwt import decode_access_token
from fastapi.security import OAuth2PasswordBearer

# Cookie name for httpOnly auth cookie
COOKIE_NAME = "access_token"

# Initialize OAuth2PasswordBearer (still used for Swagger docs, but optional in actual auth)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def get_token_from_cookie_or_header(
    request: Request,
    token_from_header: str | None = Depends(oauth2_scheme)
) -> str:
    """
    Extract JWT token from httpOnly cookie OR Authorization header.
    Priority: Cookie first (for SSR requests from SvelteKit), then header (for API clients).
    """
    # Try to get token from httpOnly cookie first
    token_from_cookie = request.cookies.get(COOKIE_NAME)
    
    if token_from_cookie:
        return token_from_cookie
    
    if token_from_header:
        return token_from_header
    
    # No token found in either location
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_data(
    token: str = Depends(get_token_from_cookie_or_header),
) -> TokenData:
    """
    Decode the JWT once and return structured token claims.
    All downstream dependencies (get_current_user, RBAC guards) depend on this —
    FastAPI caches it per request so the JWT is decoded exactly once.
    """
    payload = decode_access_token(token)
    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenData(
        user_id=user_id,
        username=payload.get("sub"),
        role=payload.get("role"),
        org_role=payload.get("org_role"),
        facility_id=payload.get("facility_id"),
    )


async def get_current_user(
    token_data: TokenData = Depends(get_token_data),
    session: Session = Depends(get_session)
) -> User:
    """
    Return the authenticated User from the database.
    Depends on get_token_data — JWT is decoded once and shared with any
    RBAC guard that also depends on get_token_data in the same request.
    """
    user = session.get(User, token_data.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.email_verified:
        raise HTTPException(403, "Email address not verified")
    return current_user