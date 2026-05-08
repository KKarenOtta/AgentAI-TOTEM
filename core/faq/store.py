from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "faq"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _company_dir(company_id: str) -> Path:
    if not company_id:
        raise ValueError("company_id é obrigatório.")

    path = DATA_DIR / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _file(company_id: str, name: str) -> Path:
    return _company_dir(company_id) / name


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_faq(company_id: str) -> list[dict[str, Any]]:
    return _load_json(_file(company_id, "faq.json"), [])


def save_faq(company_id: str, items: list[dict[str, Any]]) -> None:
    normalized = []

    for item in items:
        question = (item.get("question") or "").strip()
        answer = (item.get("answer") or "").strip()

        if not question or not answer:
            continue

        row = dict(item)
        row["faq_id"] = row.get("faq_id") or uuid4().hex
        row["question"] = question
        row["answer"] = answer
        row["intent"] = (row.get("intent") or "general").strip()
        row["score"] = float(row.get("score") or 0)
        row["uses"] = int(row.get("uses") or 0)
        row["quality_score"] = float(row.get("quality_score") or row.get("score") or 0)
        row["status"] = row.get("status") or "active"
        row["updated_at"] = row.get("updated_at") or _now()
        row["created_at"] = row.get("created_at") or row["updated_at"]

        normalized.append(row)

    _save_json(_file(company_id, "faq.json"), normalized)


def load_candidates(company_id: str) -> list[dict[str, Any]]:
    return _load_json(_file(company_id, "candidates.json"), [])


def save_candidates(company_id: str, items: list[dict[str, Any]]) -> None:
    _save_json(_file(company_id, "candidates.json"), items)


def load_corrections(company_id: str) -> list[dict[str, Any]]:
    return _load_json(_file(company_id, "corrections.json"), [])


def save_corrections(company_id: str, items: list[dict[str, Any]]) -> None:
    _save_json(_file(company_id, "corrections.json"), items)


def append_correction(company_id: str, correction: dict[str, Any]) -> dict[str, Any]:
    rows = load_corrections(company_id)

    item = dict(correction)
    item["correction_id"] = item.get("correction_id") or uuid4().hex
    item["company_id"] = company_id
    item["created_at"] = item.get("created_at") or _now()

    rows.append(item)
    save_corrections(company_id, rows)

    return item


def load_quality_history(company_id: str) -> list[dict[str, Any]]:
    return _load_json(_file(company_id, "quality_history.json"), [])


def append_quality_event(company_id: str, event: dict[str, Any]) -> dict[str, Any]:
    rows = load_quality_history(company_id)

    item = dict(event)
    item["event_id"] = item.get("event_id") or uuid4().hex
    item["company_id"] = company_id
    item["created_at"] = item.get("created_at") or _now()

    rows.append(item)
    _save_json(_file(company_id, "quality_history.json"), rows)

    return item
