from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes.dashboard import router as dashboard_router
from app.routes.api import router as api_router
from app.routes.totem import router as totem_router
from app.routes.presence import router as presence_router
from app.routes.analytics import router as analytics_router
from app.routes.faq_admin import router as faq_admin_router
from app.routes.semantic_dashboard import router as semantic_router
from app.routes.device import router as device_router
from app.routes.totem_options import router as totem_options_router

app = FastAPI(
    title="AgentAI-TOTEM",
    version="2.0.0",
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health():
    return JSONResponse(
        {
            "status": "ok",
            "app": "AgentAI-TOTEM",
            "version": "2.0.0",
            "env": os.getenv("APP_ENV", "development"),
        }
    )


app.include_router(dashboard_router)
app.include_router(api_router)
app.include_router(totem_router)
app.include_router(presence_router, prefix="/api")
app.include_router(analytics_router)
app.include_router(faq_admin_router)
app.include_router(semantic_router)

app.include_router(device_router)
app.include_router(totem_options_router)
