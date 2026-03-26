from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.company_store import load_companies, add_company, delete_company

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    companies = load_companies()
    featured_company = companies[0] if companies else None

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "request": request,
            "companies": companies,
            "featured_company": featured_company,
        },
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
