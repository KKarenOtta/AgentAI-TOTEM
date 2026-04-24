from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.company.store import add_company, delete_company, load_companies

router = APIRouter(tags=["web"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _find_company(company_id: str) -> dict | None:
    companies = load_companies()
    return next((c for c in companies if c.get("company_id") == company_id), None)


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    companies = load_companies()

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "request": request,
            "companies": companies,
            "featured_company": companies[0] if companies else None,
        },
    )


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    companies = load_companies()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "request": request,
            "companies": companies,
        },
    )


@router.post("/admin/create")
def admin_create_company(
    company_id: str = Form(...),
    name: str = Form(...),
):
    company_id = company_id.strip()
    name = name.strip()

    if company_id and name:
        add_company(company_id, name)

    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/delete/{company_id}")
def admin_delete_company(company_id: str):
    delete_company(company_id)
    return RedirectResponse(url="/admin", status_code=303)


@router.get("/client/{company_id}", response_class=HTMLResponse)
def client_dashboard(company_id: str, request: Request):
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
    return templates.TemplateResponse(
        request=request,
        name="totem_ui.html",
        context={
            "request": request,
            "company_id": company_id,
        },
    )
