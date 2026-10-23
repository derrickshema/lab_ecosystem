from fastapi import Depends, FastAPI
from labcore.auth import AccessClaims

from .auth import auth

app = FastAPI(title="EHR API", version="0.1.0")


@app.get("/health", tags=["health"])
def read_health():
    return {"status": "healthy"}


@app.get("/me", tags=["auth"])
def me(claims: AccessClaims = Depends(auth.current_claims)) -> AccessClaims:
    """Who the caller is, as EHR sees them (from their Identity token)."""
    return claims
