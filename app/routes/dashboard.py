from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
router = APIRouter(tags=["web"])

# Admin (main): lista empresas (por enquanto simples)
@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    # MVP: sem DB -> empresas fixas
    companies = [
        {"company_id": "ACME-001", "name": "ACME"},
        {"company_id": "KAREN-001", "name": "Karen Demo"},
    ]
    return templates.TemplateResponse("admin.html", {"request": request, "companies": companies})


# Cliente: dashboard por empresa (métricas via /api/metrics)
@router.get("/client/{company_id}", response_class=HTMLResponse)
def client_dashboard(company_id: str, request: Request):
    return templates.TemplateResponse("client_dashboard.html", {"request": request, "company_id": company_id})


# Cliente: campanhas (CRUD via /api/campaigns)
@router.get("/client/{company_id}/campaigns", response_class=HTMLResponse)
def client_campaigns(company_id: str, request: Request):
    return templates.TemplateResponse("campaigns.html", {"request": request, "company_id": company_id})


# Totem simulator (localhost)
@router.get("/totem/sim/{company_id}", response_class=HTMLResponse)
def totem_sim(company_id: str, request: Request):
    return templates.TemplateResponse("totem_sim.html", {"request": request, "company_id": company_id})


# Totem live monitor (SSE)
@router.get("/totem/live/{company_id}", response_class=HTMLResponse)
def totem_live(company_id: str, request: Request):
    return templates.TemplateResponse("totem_live.html", {"request": request, "company_id": company_id})