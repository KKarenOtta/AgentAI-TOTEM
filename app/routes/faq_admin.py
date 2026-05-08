from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.faq.learning import correct_faq_answer, reindex_company_faq, upsert_faq_item
from core.faq.store import (
    load_candidates,
    load_corrections,
    load_faq,
    load_quality_history,
    save_candidates,
)


router = APIRouter(prefix="/admin/faq", tags=["faq-admin"])
templates = Jinja2Templates(directory="templates")


def _user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)


def _company(user: dict | None) -> str | None:
    if not user:
        return None

    company_id = user.get("company_id")

    if company_id == "*":
        return "FLX-001"

    return company_id


def _allowed(user: dict | None) -> bool:
    return bool(user and user.get("role") in {"admin", "company"})


def _forbidden():
    return JSONResponse({"error": "forbidden"}, status_code=403)


@router.get("/", response_class=HTMLResponse)
def page(request: Request):
    user = _user(request)

    if not _allowed(user):
        return RedirectResponse("/")

    return templates.TemplateResponse(
        request=request,
        name="faq_admin.html",
        context={
            "request": request,
            "company_id": _company(user),
        },
    )


@router.get("/items")
def items(request: Request):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    return {"items": load_faq(_company(user))}


@router.get("/candidates")
def candidates(request: Request):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    return {"items": load_candidates(_company(user))}


@router.get("/corrections")
def corrections(request: Request):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    return {"items": load_corrections(_company(user))}


@router.get("/quality")
def quality(request: Request):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    return {"items": load_quality_history(_company(user))}


@router.post("/create")
def create(request: Request, payload: dict):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    item = upsert_faq_item(
        company_id=_company(user),
        question=payload.get("question"),
        answer=payload.get("answer"),
        intent=payload.get("intent") or "general",
        quality_score=float(payload.get("quality_score") or payload.get("score") or 0),
        source="manual",
    )

    return {"ok": True, "item": item}


@router.post("/correct")
def correct(request: Request, payload: dict):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    item = correct_faq_answer(
        company_id=_company(user),
        question=payload.get("question"),
        corrected_answer=payload.get("answer") or payload.get("corrected_answer"),
        intent=payload.get("intent") or "general",
        reason=payload.get("reason"),
        reviewer=user.get("username") or user.get("email") or user.get("role"),
    )

    return {"ok": True, "item": item}


@router.post("/candidate/approve")
def approve_candidate(request: Request, payload: dict):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    company_id = _company(user)
    question = payload.get("question")
    answer = payload.get("answer")

    item = upsert_faq_item(
        company_id=company_id,
        question=question,
        answer=answer,
        intent=payload.get("intent") or "general",
        quality_score=float(payload.get("quality_score") or 0.75),
        source="candidate_approved",
    )

    candidates = [
        candidate
        for candidate in load_candidates(company_id)
        if (candidate.get("question") or "").strip() != (question or "").strip()
    ]

    save_candidates(company_id, candidates)

    return {"ok": True, "item": item}


@router.post("/reindex")
def reindex(request: Request):
    user = _user(request)

    if not _allowed(user):
        return _forbidden()

    result = reindex_company_faq(_company(user))

    return {"ok": True, "result": result}
