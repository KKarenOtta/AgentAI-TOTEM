from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/admin/faq", tags=["faq-admin"])

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
FAQ_FILE = DATA_DIR / "zoo_faq.json"
CANDIDATES_FILE = DATA_DIR / "faq_candidates.json"

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _save(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/", response_class=HTMLResponse)
def faq_admin_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="faq_admin.html",
        context={"request": request},
    )


@router.get("/items")
def list_faq_items():
    return JSONResponse({"items": _load(FAQ_FILE)})


@router.get("/candidates")
def list_candidates():
    return JSONResponse({"items": _load(CANDIDATES_FILE)})


@router.post("/create")
def create_faq_item(payload: dict):
    items = _load(FAQ_FILE)

    item = {
        "question": (payload.get("question") or "").strip(),
        "answer": (payload.get("answer") or "").strip(),
        "intent": (payload.get("intent") or "geral").strip(),
    }

    if not item["question"] or not item["answer"]:
        return JSONResponse({"ok": False, "error": "question_and_answer_required"}, status_code=400)

    items = [x for x in items if x.get("question") != item["question"]]
    items.append(item)
    _save(FAQ_FILE, items)

    return {"ok": True, "item": item}


@router.post("/approve")
def approve_candidate(payload: dict):
    question = (payload.get("question") or "").strip()
    answer = (payload.get("answer") or "").strip()
    intent = (payload.get("intent") or "geral").strip()

    if not question or not answer:
        return JSONResponse({"ok": False, "error": "invalid_candidate"}, status_code=400)

    faq_items = _load(FAQ_FILE)
    faq_items = [x for x in faq_items if x.get("question") != question]
    faq_items.append({"question": question, "answer": answer, "intent": intent})
    _save(FAQ_FILE, faq_items)

    candidates = [x for x in _load(CANDIDATES_FILE) if x.get("question") != question]
    _save(CANDIDATES_FILE, candidates)

    return {"ok": True}


@router.post("/reject")
def reject_candidate(payload: dict):
    question = (payload.get("question") or "").strip()

    candidates = [x for x in _load(CANDIDATES_FILE) if x.get("question") != question]
    _save(CANDIDATES_FILE, candidates)

    return {"ok": True}


@router.delete("/items")
def delete_faq_item(payload: dict):
    question = (payload.get("question") or "").strip()

    items = [x for x in _load(FAQ_FILE) if x.get("question") != question]
    _save(FAQ_FILE, items)

    return {"ok": True}
