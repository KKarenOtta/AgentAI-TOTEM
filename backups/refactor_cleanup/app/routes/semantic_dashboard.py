from fastapi import APIRouter
from fastapi.responses import JSONResponse
import json
from pathlib import Path

router = APIRouter(prefix="/semantic", tags=["semantic"])

BASE = Path("data")


@router.get("/dashboard")
def dashboard():
    def load(name):
        p = BASE / name
        return json.loads(p.read_text()) if p.exists() else {}

    return JSONResponse({
        "errors": load("error_dashboard.json"),
        "clusters": load("question_clusters.json"),
        "candidates": load("faq_candidates.json"),
        "config": load("semantic_config.json")
    })
