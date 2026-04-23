from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.company_store import load_companies, add_company, delete_company
from services.totem.coupon_store import (
    list_coupons_by_lead,
    redeem_coupon,
    get_coupon_by_id,
)
from services.totem.lead_store import save_lead
from services.totem.recovery_store import (
    get_recovery_memory,
    get_lead_by_id,
    get_latest_memory_for_lead,
    get_session_handoff,
)

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["web"])


def _merge_recommendations_with_coupons(
    recommendations: list[dict],
    coupons: list[dict],
) -> list[dict]:
    coupons_by_campaign: dict[str, list[dict]] = {}
    for coupon in coupons:
        campaign_id = coupon.get("campaign_id")
        if not campaign_id:
            continue
        coupons_by_campaign.setdefault(campaign_id, []).append(coupon)

    merged: list[dict] = []
    for item in recommendations:
        campaign_id = item.get("campaign_id")
        related_coupons = coupons_by_campaign.get(campaign_id, [])

        merged_item = dict(item)
        merged_item["issued_coupons"] = related_coupons
        merged.append(merged_item)

    return merged


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    companies = load_companies()
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"request": request, "companies": companies},
    )


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    companies = load_companies()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"request": request, "companies": companies},
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
    return templates.TemplateResponse(
        request=request,
        name="client_dashboard.html",
        context={"request": request, "company_id": company_id},
    )


@router.get("/client/{company_id}/campaigns", response_class=HTMLResponse)
def client_campaigns(company_id: str, request: Request):
    return templates.TemplateResponse(
        request=request,
        name="campaigns.html",
        context={"request": request, "company_id": company_id},
    )


@router.get("/totem/sim/{company_id}", response_class=HTMLResponse)
def totem_sim(company_id: str, request: Request):
    return templates.TemplateResponse(
        request=request,
        name="totem_sim.html",
        context={"request": request, "company_id": company_id},
    )


@router.get("/totem/live/{company_id}", response_class=HTMLResponse)
def totem_live(company_id: str, request: Request):
    return templates.TemplateResponse(
        request=request,
        name="totem_live.html",
        context={"request": request, "company_id": company_id},
    )


@router.get("/mobile/start/{session_id}", response_class=HTMLResponse)
def mobile_start(session_id: str, request: Request):
    handoff = get_session_handoff(session_id)

    return templates.TemplateResponse(
        request=request,
        name="mobile_start.html",
        context={"request": request, "session_id": session_id, "handoff": handoff},
        status_code=200 if handoff else 404,
    )


@router.get("/mobile/capture/{session_id}", response_class=HTMLResponse)
def mobile_capture(session_id: str, request: Request):
    handoff = get_session_handoff(session_id)

    return templates.TemplateResponse(
        request=request,
        name="mobile_capture.html",
        context={"request": request, "session_id": session_id, "handoff": handoff},
        status_code=200 if handoff else 404,
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
        return RedirectResponse(url=f"/mobile/start/{session_id}", status_code=303)

    brands = [b.strip() for b in favorite_brands.split(",") if b.strip()]

    lead = save_lead(
        {
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
            "research_summary": handoff.get("research_summary"),
            "recommendations_snapshot": handoff.get("recommendations_snapshot"),
            "consent_text": "Autorizo o tratamento dos meus dados para acesso às ofertas, newsletter e recuperação resumida do atendimento.",
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request.client.host if request.client else None,
        }
    )

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
        request=request,
        name="mobile_content.html",
        context={
            "request": request,
            "lead": lead,
            "memory": memory,
            "recommendations": recommendations,
            "recommended_coupons": recommended_coupons,
            "coupons": coupons,
        },
        status_code=200 if lead else 404,
    )


@router.get("/recovery/{memory_id}", response_class=HTMLResponse)
def recovery_page(memory_id: str, request: Request):
    memory = get_recovery_memory(memory_id)
    if not memory:
        return templates.TemplateResponse(
            request=request,
            name="recovery_mobile.html",
            context={
                "request": request,
                "title": "Recuperação",
                "mode": "missing",
                "lead": None,
                "memory": None,
                "recommendations": [],
                "coupons": [],
            },
            status_code=404,
        )

    lead = get_lead_by_id(memory.get("lead_id", ""))
    recommendations = (memory.get("recommendations_snapshot") or {}).get("top_actions", [])
    coupons = list_coupons_by_lead(memory.get("lead_id", ""))

    return templates.TemplateResponse(
        request=request,
        name="recovery_mobile.html",
        context={
            "request": request,
            "title": "Recuperação da pesquisa",
            "mode": "recovery",
            "lead": lead,
            "memory": memory,
            "recommendations": recommendations,
            "coupons": coupons,
        },
    )


@router.get("/lead/access/{lead_id}", response_class=HTMLResponse)
def lead_access_page(lead_id: str, request: Request):
    lead = get_lead_by_id(lead_id)
    if not lead:
        return templates.TemplateResponse(
            request=request,
            name="recovery_mobile.html",
            context={
                "request": request,
                "title": "Acesso",
                "mode": "missing",
                "lead": None,
                "memory": None,
                "recommendations": [],
                "coupons": [],
            },
            status_code=404,
        )

    memory = get_latest_memory_for_lead(lead_id)
    recommendations = []
    if memory:
        recommendations = (memory.get("recommendations_snapshot") or {}).get("top_actions", [])

    coupons = list_coupons_by_lead(lead_id)

    return templates.TemplateResponse(
        request=request,
        name="recovery_mobile.html",
        context={
            "request": request,
            "title": "Acesso do usuário",
            "mode": "access",
            "lead": lead,
            "memory": memory,
            "recommendations": recommendations,
            "coupons": coupons,
        },
    )


@router.get("/store/redeem", response_class=HTMLResponse)
def store_redeem_page(
    request: Request,
    coupon_id: str | None = None,
    store_id: str | None = None,
):
    coupon = None
    if coupon_id:
        coupon = get_coupon_by_id(coupon_id.strip())

    return templates.TemplateResponse(
        request=request,
        name="store_redeem.html",
        context={
            "request": request,
            "result": coupon,
            "coupon_id": coupon_id or "",
            "store_id": store_id or "",
            "operator_id": "",
            "just_validated": False,
        },
    )


@router.post("/store/redeem", response_class=HTMLResponse)
def store_redeem_submit(
    request: Request,
    coupon_id: str = Form(...),
    store_id: str = Form(""),
    operator_id: str = Form(""),
):
    coupon = redeem_coupon(
        coupon_id=coupon_id.strip(),
        store_id=store_id.strip() or None,
        operator_id=operator_id.strip() or None,
    )

    return templates.TemplateResponse(
        request=request,
        name="store_redeem.html",
        context={
            "request": request,
            "result": coupon,
            "coupon_id": coupon_id,
            "store_id": store_id,
            "operator_id": operator_id,
            "just_validated": True,
        },
    )
