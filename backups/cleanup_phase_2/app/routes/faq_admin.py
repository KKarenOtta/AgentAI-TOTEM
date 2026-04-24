from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
import json
from pathlib import Path

router = APIRouter(prefix="/admin/faq", tags=["faq-admin"])

BASE = Path("data")
CANDIDATES = BASE / "faq_candidates.json"
FAQ = BASE / "zoo_faq.json"


def load(p):
    return json.loads(p.read_text()) if p.exists() else []


def save(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@router.get("/", response_class=HTMLResponse)
def page():
    return (BASE / "faq_admin.html").read_text()


@router.get("/candidates")
def get_candidates():
    return JSONResponse(load(CANDIDATES))


@router.post("/approve")
def approve(item: dict):
    faq = load(FAQ)
    faq.append(item)
    save(FAQ, faq)

    candidates = load(CANDIDATES)
    candidates = [c for c in candidates if c["question"] != item["question"]]
    save(CANDIDATES, candidates)

    return {"ok": True}


@router.post("/reject")
def reject(item: dict):
    candidates = load(CANDIDATES)
    candidates = [c for c in candidates if c["question"] != item["question"]]
    save(CANDIDATES, candidates)

    return {"ok": True}
