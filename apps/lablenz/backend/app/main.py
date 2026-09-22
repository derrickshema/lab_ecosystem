from fastapi import FastAPI

from .routes.auth import router as auth_router
from .routes.users import router as users_router

app = FastAPI(title="Lablenz API", version="0.1.0")

app.include_router(auth_router)
app.include_router(users_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
