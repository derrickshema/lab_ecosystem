from fastapi import FastAPI

from .routes.auth import router as auth_router
from .routes.facilities import router as facilities_router
from .routes.users import router as users_router
from .security.jwt import public_jwks

app = FastAPI(title="Identity API", version="0.1.0")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(facilities_router)


@app.get("/.well-known/jwks.json", tags=["keys"])
def jwks() -> dict:
    """Public signing key(s). Other apps fetch this to verify access tokens."""
    return public_jwks()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
