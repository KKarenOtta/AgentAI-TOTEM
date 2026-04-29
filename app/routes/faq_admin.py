from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.faq.store import load_faq, save_faq, load_candidates, save_candidates

router = APIRouter(prefix="/admin/faq", tags=["faq-admin"])

templates = Jinja2Templates(directory="templates")


def _user(request: Request):
    return getattr(request.state, "user", None)


def _company(user):
    if not user:
        return None
    return user.get("company_id")


def _allowed(user):
    return user and user.get("role") in ("admin", "company")


@router.get("/", response_class=HTMLResponse)
def page(request: Request):
    user = _user(request)
    if not _allowed(user):
        return RedirectResponse("/")

    return templates.TemplateResponse(
        request=request,
        name="faq_admin.html",
        context={"request": request},
    )


@router.get("/items")
def items(request: Request):
    user = _user(request)
    if not _allowed(user):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    return {"items": load_faq(_company(user))}


@router.get("/candidates")
def candidates(request: Request):
    user = _user(request)
    if not _allowed(user):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    return {"items": load_candidates(_company(user))}


@router.post("/create")
def create(request: Request, payload: dict):
    user = _user(request)
    if not _allowed(user):
        return JSONResponse({"error": "forbidden"}, status_code=403)

    company_id = _company(user)

    faq = load_faq(company_id)

    item = {
        "question": payload["question"],
        "answer": payload["answer"],
        "intent": payload.get("intent", "geral"),
        "score": 0,
        "uses": 0
    }

    faq = [x for x in faq if x["question"] != item["question"]]
    faq.append(item)

    save_faq(company_id, faq)

    return {"ok": True}
