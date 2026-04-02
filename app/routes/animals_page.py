from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/animals-view")
def animals_view(request: Request):
    return templates.TemplateResponse("animals.html", {"request": request})
