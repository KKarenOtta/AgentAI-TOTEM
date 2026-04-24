from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.company_store import load_companies, add_company, delete_company

from core.totem.coupon_store import (
    list_coupons_by_lead,
    redeem_coupon,
    get_coupon_by_id,
)

from core.totem.lead_store import save_lead

from core.totem.recovery_store import (
    get_recovery_memory,
    get_lead_by_id,
    get_latest_memory_for_lead,
    get_session_handoff,
)

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["web"])


def _merge_recommendations_with_coupons(recommendations, coupons):
    coupons_by_campaign = {}

    for coupon in coupons:
        campaign_id = coupon.get("campaign_id")
        if not campaign_id:
            continue
        coupons_by_campaign.setdefault(campaign_id, []).append(coupon)

    merged = []

    for item in recommendations:
        campaign_id = item.get("campaign_id")
        related = coupons_by_campaign.get(campaign_id, [])

        merged.append({
            **item,
            "issued_coupons": related
        })

    return merged


# =========================
# HOME / ADMIN
# =========================

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    companies = load_companies()
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "companies": companies}
    )


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    companies = load_companies()
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "companies": companies}
    )


@router.post("/admin/create")
def admin_create_company(company_id: str = Form(...), name: str = Form(...)):
    if company_id.strip() and name.strip():
        add_company(company_id.strip(), name.strip())

    return RedirectResponse("/admin", status_code=303)


@router.post("/admin/delete/{company_id}")
def admin_delete_company(company_id: str):
    delete_company(company_id)
    return RedirectResponse("/admin", status_code=303)


# =========================
# CLIENT
# =========================

@router.get("/client/{company_id}", response_class=HTMLResponse)
def client_dashboard(company_id: str, request: Request):
    return templates.TemplateResponse(
        "client_dashboard.html",
        {"request": request, "company_id": company_id}
    )


@router.get("/client/{company_id}/campaigns", response_class=HTMLResponse)
def client_campaigns(company_id: str, request: Request):
    return templates.TemplateResponse(
        "campaigns.html",
        {"request": request, "company_id": company_id}
    )


# =========================
# MOBILE FLOW
# =========================

@router.get("/mobile/start/{session_id}", response_class=HTMLResponse)
def mobile_start(session_id: str, request: Request):
    handoff = get_session_handoff(session_id)

    return templates.TemplateResponse(
        "mobile_start.html",
        {
            "request": request,
            "session_id": session_id,
            "handoff": handoff
        },
        status_code=200 if handoff else 404
    )


@router.get("/mobile/capture/{session_id}", response_class=HTMLResponse)
def mobile_capture(session_id: str, request: Request):
    handoff = get_session_handoff(session_id)

    return templates.TemplateResponse(
        "mobile_capture.html",
        {
            "request": request,
            "session_id": session_id,
            "handoff": handoff
        },
        status_code=200 if handoff else 404
    )


@router.post("/mobile/capture/{session_id}")
def mobile_capture_submit(
    session_id: str,
    request: Request,
    full_name: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    email: str = Form(...),
    cpf: str = Form(""),
    favorite_brands: str = Form(""),
    lgpd_consent: bool = Form(False),
):
    handoff = get_session_handoff(session_id)

    if not handoff:
        return RedirectResponse(f"/mobile/start/{session_id}", status_code=303)

    brands = [b.strip() for b in favorite_brands.split(",") if b.strip()]

    lead = save_lead({
        "company_id": handoff["company_id"],
        "session_id": session_id,
        "full_name": full_name,
        "age": age,
        "gender": gender,
        "email": email,
        "cpf": cpf,
        "favorite_brands": brands,
        "lgpd_consent": lgpd_consent,
        "source": "mobile_capture",
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
    })

    return RedirectResponse(f"/mobile/content/{lead['lead_id']}", status_code=303)


@router.get("/mobile/content/{lead_id}", response_class=HTMLResponse)
def mobile_content(lead_id: str, request: Request):
    lead = get_lead_by_id(lead_id)
    memory = get_latest_memory_for_lead(lead_id)
    coupons = list_coupons_by_lead(lead_id)

    recommendations = []
    if memory:
        recommendations = (memory.get("recommendations_snapshot") or {}).get("top_actions", [])

    recommended_coupons = _merge_recommendations_with_coupons(recommendations, coupons)

    return templates.TemplateResponse(
        "mobile_content.html",
        {
            "request": request,
            "lead": lead,
            "memory": memory,
            "recommendations": recommendations,
            "recommended_coupons": recommended_coupons,
            "coupons": coupons,
        },
        status_code=200 if lead else 404,
    )


# =========================
# RECOVERY
# =========================

@router.get("/recovery/{memory_id}", response_class=HTMLResponse)
def recovery_page(memory_id: str, request: Request):
    memory = get_recovery_memory(memory_id)

    if not memory:
        return templates.TemplateResponse(
            "recovery_mobile.html",
            {"request": request, "mode": "missing"},
            status_code=404
        )

    lead = get_lead_by_id(memory.get("lead_id", ""))
    recommendations = (memory.get("recommendations_snapshot") or {}).get("top_actions", [])
    coupons = list_coupons_by_lead(memory.get("lead_id", ""))

    return templates.TemplateResponse(
        "recovery_mobile.html",
        {
            "request": request,
            "lead": lead,
            "memory": memory,
            "recommendations": recommendations,
            "coupons": coupons,
        }
    )
