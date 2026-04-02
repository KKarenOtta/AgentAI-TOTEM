from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.api import router as api_router
from app.routes.dashboard import router as dashboard_router
from app.routes.presence import router as presence_router
from app.routes.totem import router as totem_router
from core.logging import configure_logging
from app.routes.test_db import router as test_db_router

configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(dashboard_router)
app.include_router(totem_router, prefix="/totem", tags=["totem"])
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(presence_router, prefix="/api", tags=["presence"])
app.include_router(test_db_router, prefix="/api", tags=["test_db"])

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }
