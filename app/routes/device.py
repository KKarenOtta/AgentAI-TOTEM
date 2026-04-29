from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.totem.coupon_store import create_coupon, get_coupon_by_id, list_coupons_by_lead, redeem_coupon
from core.totem.lead_store import find_existing_lead, save_lead
from marketing.campaigns import get_active_campaigns

BASE_DIR = Path(__file__).resolve().parent.parent.parent
HANDOFF_DIR = BASE_DIR / "data" / "device_handoffs"

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter(tags=["device"])


def _load_handoff(session_id: str) -> dict:
    path = HANDOFF_DIR / f"{session_id}.json"

    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _active_coupon_campaigns(company_id: str) -> list[dict]:
    campaigns = get_active_campaigns(company_id)
    valid = []

    for campaign in campaigns:
        if campaign.get("status") != "active":
            continue

        has_coupon = bool((campaign.get("coupon_code") or "").strip())
        has_discount = float(campaign.get("discount_value") or 0) > 0

        if has_coupon or has_discount:
            valid.append(campaign)

    return valid


def _issue_coupons(lead: dict) -> list[dict]:
    coupons = []

    for campaign in _active_coupon_campaigns(lead["company_id"]):
        coupon = create_coupon(lead, campaign)

        if coupon:
            coupons.append(coupon)

    return coupons


def _find_registered_lead(company_id: str, session_id: str) -> dict | None:
    return find_existing_lead(
        company_id=company_id,
        session_id=session_id,
        email=None,
        cpf=None,
    )


@router.get("/device/{company_id}/{session_id}", response_class=HTMLResponse)
def device_login(company_id: str, session_id: str, request: Request):
    handoff = _load_handoff(session_id)

    return templates.TemplateResponse(
        request=request,
        name="device_login.html",
        context={
            "request": request,
            "company_id": company_id,
            "session_id": session_id,
            "handoff": handoff,
        },
        status_code=200 if handoff else 404,
    )


@router.post("/device/{company_id}/{session_id}/register")
def device_register(
    company_id: str,
    session_id: str,
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    cpf: str = Form(...),
    lgpd_consent: str = Form("off"),
):
    handoff = _load_handoff(session_id)

    if not handoff:
        return templates.TemplateResponse(
            request=request,
            name="device_login.html",
            context={
                "request": request,
                "company_id": company_id,
                "session_id": session_id,
                "handoff": {},
                "error": "Sessão não encontrada. Gere um novo QR Code no totem.",
            },
            status_code=404,
        )

    if lgpd_consent != "on":
        return templates.TemplateResponse(
            request=request,
            name="device_login.html",
            context={
                "request": request,
                "company_id": company_id,
                "session_id": session_id,
                "handoff": handoff,
                "error": "É necessário aceitar os termos LGPD.",
            },
            status_code=400,
        )

    lead = save_lead(
        {
            "company_id": company_id,
            "session_id": session_id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "cpf": cpf,
            "age": 0,
            "gender": "unknown",
            "lgpd_consent": True,
            "source": "device_handoff",
            "research_summary": handoff.get("summary") or "",
            "recommendations_snapshot": handoff.get("recommendations") or {},
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
    )

    _issue_coupons(lead)

    return RedirectResponse(
        url=f"/device/{company_id}/{session_id}/offers",
        status_code=303,
    )


@router.get("/device/{company_id}/{session_id}/offers", response_class=HTMLResponse)
def device_offers(company_id: str, session_id: str, request: Request):
    handoff = _load_handoff(session_id)

    if not handoff:
        return RedirectResponse(
            url=f"/device/{company_id}/{session_id}",
            status_code=303,
        )

    lead = _find_registered_lead(company_id, session_id)

    if not lead:
        return RedirectResponse(
            url=f"/device/{company_id}/{session_id}",
            status_code=303,
        )

    _issue_coupons(lead)
    coupons = list_coupons_by_lead(lead["lead_id"])

    return templates.TemplateResponse(
        request=request,
        name="device_offers.html",
        context={
            "request": request,
            "company_id": company_id,
            "session_id": session_id,
            "handoff": handoff,
            "lead": lead,
            "coupons": coupons,
        },
    )


@router.get("/campaign/coupon/{coupon_id}", response_class=HTMLResponse)
def campaign_coupon(coupon_id: str, request: Request):
    coupon = get_coupon_by_id(coupon_id)

    return templates.TemplateResponse(
        request=request,
        name="campaign_coupon.html",
        context={
            "request": request,
            "coupon": coupon,
        },
        status_code=200 if coupon else 404,
    )


@router.get("/store/redeem", response_class=HTMLResponse)
def store_redeem_page(coupon_id: str, request: Request):
    coupon = redeem_coupon(coupon_id=coupon_id)

    return templates.TemplateResponse(
        request=request,
        name="store_redeem_result.html",
        context={
            "request": request,
            "coupon": coupon,
        },
        status_code=200 if coupon else 404,
    )
