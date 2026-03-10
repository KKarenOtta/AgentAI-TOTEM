from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.company_store import load_companies, add_company, delete_company

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["web"])

# Admin: lista empresas (via JSON)
@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    companies = load_companies()
    return templates.TemplateResponse("admin.html", {"request": request, "companies": companies})

# Admin: criar empresa
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

# Admin: deletar empresa
@router.post("/admin/delete/{company_id}")
def admin_delete_company(company_id: str):
    delete_company(company_id)
    return RedirectResponse(url="/admin", status_code=303)

# Cliente: dashboard por empresa
@router.get("/client/{company_id}", response_class=HTMLResponse)
def client_dashboard(company_id: str, request: Request):
    return templates.TemplateResponse("client_dashboard.html", {"request": request, "company_id": company_id})

# Cliente: campanhas
@router.get("/client/{company_id}/campaigns", response_class=HTMLResponse)
def client_campaigns(company_id: str, request: Request):
    return templates.TemplateResponse("campaigns.html", {"request": request, "company_id": company_id})

# Totem simulator
@router.get("/totem/sim/{company_id}", response_class=HTMLResponse)
def totem_sim(company_id: str, request: Request):
    return templates.TemplateResponse("totem_sim.html", {"request": request, "company_id": company_id})

# Totem live monitor
@router.get("/totem/live/{company_id}", response_class=HTMLResponse)
def totem_live(company_id: str, request: Request):
    return templates.TemplateResponse("totem_live.html", {"request": request, "company_id": company_id})