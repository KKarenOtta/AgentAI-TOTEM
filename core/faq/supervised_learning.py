from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ml.semantic.auto_train import index_faq


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _company_dir(company_id: str) -> Path:
    path = Path("data/faq") / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def record_feedback(
    company_id: str,
    question: str,
    answer: str,
    approved: bool,
    corrected_answer: str | None = None,
    confidence_score: float | None = None,
    source: str = "admin_review",
) -> dict[str, Any]:
    company_path = _company_dir(company_id)
    path = company_path / "quality_history.json"

    row = {
        "created_at": _now(),
        "company_id": company_id,
        "question": question.strip(),
        "answer": answer.strip(),
        "corrected_answer": (corrected_answer or "").strip(),
        "approved": bool(approved),
        "confidence_score": float(confidence_score or 0),
        "source": source,
        "status": "approved" if approved else "needs_review",
    }

    rows = []
    if path.exists():
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            rows = []

    if not isinstance(rows, list):
        rows = []

    rows.append(row)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    if approved:
        rebuild_embeddings(company_id)

    return row


def rebuild_embeddings(company_id: str) -> dict[str, Any]:
    indexed = index_faq(company_id)
    return {
        "company_id": company_id,
        "faq_embeddings_indexed": indexed,
        "status": "ok",
        "rebuilt_at": _now(),
    }


def approval_pipeline(company_id: str) -> dict[str, Any]:
    candidates_path = Path("data/faq_candidates.json")
    if not candidates_path.exists():
        return {"approved": 0, "pending": 0}

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    approved = 0
    pending = 0

    for item in candidates:
        if item.get("company_id") != company_id:
            continue

        if item.get("status") == "approved":
            record_feedback(
                company_id=company_id,
                question=item.get("question") or "",
                answer=item.get("answer") or "",
                approved=True,
                confidence_score=float(item.get("avg_score") or 0),
                source="candidate_approval",
            )
            approved += 1
        else:
            pending += 1

    return {"approved": approved, "pending": pending}
