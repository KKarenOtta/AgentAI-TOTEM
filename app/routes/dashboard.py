from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth.service import delete_user, public_users, upsert_company_user
from core.company.store import add_company, delete_company, load_companies

router = APIRouter(tags=["web"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _current_user(request: Request) -> dict:
    return getattr(request.state, "user", {}) or {}


def _is_admin(user: dict) -> bool:
    return user.get("role") == "admin"


def _user_company_id(user: dict) -> str | None:
    company_id = user.get("company_id")
    if not company_id or company_id == "*":
        return None
    return company_id


def _find_company(company_id: str) -> dict | None:
    companies = load_companies()
    return next((c for c in companies if c.get("company_id") == company_id), None)


def _visible_companies(user: dict) -> list[dict]:
    companies = load_companies()

    if _is_admin(user):
        return companies

    company_id = _user_company_id(user)
    if not company_id:
        return []

    company = next((c for c in companies if c.get("company_id") == company_id), None)
    return [company] if company else []


def _can_access_company(user: dict, company_id: str) -> bool:
    if _is_admin(user):
        return True

    return _user_company_id(user) == company_id


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = _current_user(request)
    companies = _visible_companies(user)

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "request": request,
            "companies": companies,
            "featured_company": companies[0] if companies else None,
            "is_admin": _is_admin(user),
        },
    )


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    user = _current_user(request)

    if not _is_admin(user):
        return RedirectResponse(url="/", status_code=303)

    companies = load_companies()
    users = public_users()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "request": request,
            "companies": companies,
            "users": users,
        },
    )


@router.post("/admin/create")
def admin_create_company(
    request: Request,
    company_id: str = Form(...),
    name: str = Form(...),
):
    user = _current_user(request)

    if not _is_admin(user):
        return RedirectResponse(url="/", status_code=303)

    company_id = company_id.strip()
    name = name.strip()

    if company_id and name:
        add_company(company_id, name)

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/delete/{company_id}")
def admin_delete_company(company_id: str, request: Request):
    user = _current_user(request)

    if not _is_admin(user):
        return RedirectResponse(url="/", status_code=303)

    delete_company(company_id)
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/save")
def admin_save_company_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    company_id: str = Form(...),
):
    user = _current_user(request)

    if not _is_admin(user):
        return RedirectResponse(url="/", status_code=303)

    upsert_company_user(
        username=username,
        password=password,
        company_id=company_id,
    )

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/delete/{username}")
def admin_delete_company_user(username: str, request: Request):
    user = _current_user(request)

    if not _is_admin(user):
        return RedirectResponse(url="/", status_code=303)

    delete_user(username)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/client/{company_id}", response_class=HTMLResponse)
def client_dashboard(company_id: str, request: Request):
    user = _current_user(request)

    if not _can_access_company(user, company_id):
        return RedirectResponse(url="/", status_code=303)

    company = _find_company(company_id)

    return templates.TemplateResponse(
        request=request,
        name="client_dashboard.html",
        context={
            "request": request,
            "company_id": company_id,
            "company": company,
        },
        status_code=200 if company else 404,
    )


@router.get("/client/{company_id}/campaigns", response_class=HTMLResponse)
def client_campaigns(company_id: str, request: Request):
    user = _current_user(request)

    if not _can_access_company(user, company_id):
        return RedirectResponse(url="/", status_code=303)

    company = _find_company(company_id)

    return templates.TemplateResponse(
        request=request,
        name="campaigns.html",
        context={
            "request": request,
            "company_id": company_id,
            "company": company,
        },
        status_code=200 if company else 404,
    )


@router.get("/totem/{company_id}", response_class=HTMLResponse)
def totem_ui(company_id: str, request: Request):
    raspberry_voice_server_url = os.getenv(
        "RASPBERRY_VOICE_SERVER_URL",
        os.getenv("VOICE_SERVER_URL", ""),
    ).strip().rstrip("/")

    return templates.TemplateResponse(
        request=request,
        name="totem_ui.html",
        context={
            "request": request,
            "company_id": company_id,
            "raspberry_voice_server_url": raspberry_voice_server_url,
        },
    )
