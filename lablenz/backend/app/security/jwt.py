from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import HTTPException, status

# Import centralized settings
from ..config import settings

# ---Token Generation---
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire  = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.JWTError:
         # This catches various JWT errors like invalid signature, expired token, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}, # Standard header for OAuth2
        )


# ---Password Reset Tokens---
RESET_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes

def create_password_reset_token(email: str) -> str:
    """
    Create a JWT token for password reset.
    
    Uses a different 'purpose' claim to distinguish it from access tokens.
    This prevents someone from using a reset token as an auth token.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": email,
        "purpose": "password_reset",  # Important: distinguishes from access tokens
        "exp": expire
    }
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str) -> str | None:
    """
    Verify a password reset token and return the email.
    
    Returns:
        The email address if token is valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Verify this is actually a password reset token
        if payload.get("purpose") != "password_reset":
            return None
        
        email: str = payload.get("sub")
        return email
        
    except jwt.JWTError:
        return None