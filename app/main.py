from __future__ import annotations


from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from core.auth.session_store import get_session
from app.routes.rag_test import router as rag_test_router
from app.routes.dashboard import router as dashboard_router
from app.routes.api import router as api_router
from app.routes.totem import router as totem_router
from app.routes.presence import router as presence_router
from app.routes.analytics import router as analytics_router
from app.routes.faq_admin import router as faq_admin_router
from app.routes.semantic_dashboard import router as semantic_router
from app.routes.device import router as device_router
from app.routes.totem_options import router as totem_options_router
from app.routes.auth import router as auth_router
from app.routes.audio import router as audio_router
from app.routes.voice_status import router as voice_status_router
from app.routes.voice_control import router as voice_control_router
from app.routes.voice_upload import router as voice_upload_router
from core.totem.orchestrator import start_presence_listener
from app.services.aws_db_service import init_db_pool, close_db_pool

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ROUTERS
app.include_router(rag_test_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(api_router)
app.include_router(totem_router)
app.include_router(audio_router)
app.include_router(voice_status_router)
app.include_router(voice_control_router)
app.include_router(presence_router)
app.include_router(analytics_router)
app.include_router(faq_admin_router)
app.include_router(semantic_router)
app.include_router(device_router)
app.include_router(totem_options_router)
app.include_router(voice_upload_router)


@app.on_event("startup")
async def startup_event():
    import os

    if os.getenv("AWS_DB_STARTUP_ENABLED", "false").strip().lower() in {"1", "true", "yes"}:
        await init_db_pool()

    start_presence_listener()


@app.on_event("shutdown")
async def shutdown_event():
    await close_db_pool()

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    public = [
        "/login",
        "/device",
        "/store",
        "/campaign",
        "/totem",
        "/api",
        "/static",
        "/rag-test",
        "/api/rag-test",
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
