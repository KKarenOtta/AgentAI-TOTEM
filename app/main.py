from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from core.config.runtime import IS_EDGE, IS_CLOUD
from core.auth.session_store import get_session
from app.routes.auth import router as auth_router


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
BETA_STATIC_DIR = BASE_DIR / "beta_integration" / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/beta-static", StaticFiles(directory=str(BETA_STATIC_DIR)), name="beta_static")

app.include_router(auth_router)

if IS_EDGE:
    from app.routes.rag_test import router as rag_test_router
    from app.routes.edge_status import router as edge_status_router
    from app.routes.integration_ui import router as integration_ui_router
    from app.routes.dashboard import router as dashboard_router
    from app.routes.api import router as api_router
    from app.routes.analytics import router as analytics_router
    from app.routes.faq_admin import router as faq_admin_router
    from app.routes.semantic_dashboard import router as semantic_router
    from app.routes.device import router as device_router
    from app.routes.totem_options import router as totem_options_router
    from app.routes.audio import router as audio_router
    from app.routes.voice_status import router as voice_status_router
    from app.routes.edge_ws import router as edge_ws_router
    from app.routes.edge_audio import router as edge_audio_router
    from app.routes.edge_text import router as edge_text_router
    from app.routes.totem import router as totem_router
    from app.routes.edge_session import router as edge_session_router
    from app.routes.edge_session_start import router as edge_session_start_router

    app.include_router(rag_test_router)
    app.include_router(edge_status_router)
    app.include_router(integration_ui_router)
    app.include_router(dashboard_router)
    app.include_router(api_router)
    app.include_router(audio_router)
    app.include_router(voice_status_router)
    app.include_router(analytics_router)
    app.include_router(faq_admin_router)
    app.include_router(semantic_router)
    app.include_router(device_router)
    app.include_router(totem_options_router)
    app.include_router(edge_ws_router)
    app.include_router(edge_audio_router)
    app.include_router(edge_text_router)
    app.include_router(totem_router)
    app.include_router(edge_session_router)
    app.include_router(edge_session_start_router)

if IS_CLOUD:
    from app.routes.cloud_interact import router as cloud_interact_router
    from app.routes.totem import router as totem_router

    app.include_router(cloud_interact_router)
    app.include_router(totem_router)

@app.on_event("startup")
async def startup_event():
    if os.getenv("AWS_DB_STARTUP_ENABLED", "false").strip().lower() in {"1", "true", "yes"}:
        from app.services.aws_db_service import init_db_pool
        await init_db_pool()


@app.on_event("shutdown")
async def shutdown_event():
    from app.services.aws_db_service import close_db_pool
    await close_db_pool()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    public = [
        "/login",
        "/favicon.ico",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/integration",
        "/beta-static",
        "/device",
        "/store",
        "/campaign",
        "/totem",
        "/api",
        "/static",
        "/rag-test",
        "/api/rag-test",
        "/cloud",
        "/ws",
        "/audio-file",
        "/edge",
        "/edge/status",
    ]

    if any(path.startswith(p) for p in public):
        return await call_next(request)

    session_id = request.cookies.get("session_id")

    if not session_id:
        return RedirectResponse("/login")

    session = get_session(session_id)

    if not session:
        return RedirectResponse("/login")

    user = session["user"]
    request.state.user = user

    if path.startswith("/admin/faq"):
        if user["role"] not in ("admin", "company"):
            return RedirectResponse("/")

    elif path.startswith("/admin") and user["role"] != "admin":
        return RedirectResponse("/")

    if path.startswith("/client"):
        if user["role"] == "company":
            parts = path.split("/")
            company_id = parts[2] if len(parts) > 2 else None

            if company_id != user["company_id"]:
                return RedirectResponse("/")

    return await call_next(request)
    
@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}    
