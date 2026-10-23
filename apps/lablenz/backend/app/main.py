from fastapi import Depends, FastAPI
from labcore.auth import AccessClaims

from .auth import auth

app = FastAPI(title="Lablenz API", version="0.1.0")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/me", tags=["auth"])
def me(claims: AccessClaims = Depends(auth.current_claims)) -> AccessClaims:
    """Who the caller is, as LabLenz sees them (from their Identity token)."""
    return claims
