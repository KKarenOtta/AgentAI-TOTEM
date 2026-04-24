from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DATA_PATH = Path("data/company_contexts.json")


def load_all_company_contexts() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {}

    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_company_context(company_id: str) -> dict[str, Any]:
    data = load_all_company_contexts()
    context = data.get(company_id, {})

    if not isinstance(context, dict):
        return {}

    return context


def save_all_company_contexts(data: dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
