from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OPTIONS_FILE = BASE_DIR / "data" / "totem_options.json"

router = APIRouter(tags=["totem-options"])


def _load():
    if not OPTIONS_FILE.exists():
        return {}

    try:
        return json.loads(OPTIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


@router.get("/api/totem-options/{company_id}")
def list_totem_options(company_id: str):
    data = _load()
    options = data.get(company_id) or data.get("default") or []

    return JSONResponse({"options": options[:3]})
