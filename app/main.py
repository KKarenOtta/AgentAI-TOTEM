from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes.dashboard import router as dashboard_router
from app.routes.api import router as api_router
from app.routes.totem import router as totem_router

app = FastAPI(
    title="AgentAI-TOTEM",
    version="1.0.0",
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
            "env": os.getenv("APP_ENV", "development"),
        }
    )


app.include_router(dashboard_router)
app.include_router(api_router)
app.include_router(totem_router)

try:
    from app.routes.test_db import router as test_db_router
    app.include_router(test_db_router)
except Exception as exc:
    print(f"[WARN] test_db router não carregado: {exc}")
