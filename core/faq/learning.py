from __future__ import annotations

from datetime import datetime
from typing import Any

from core.faq.store import (
    append_correction,
    append_quality_event,
    load_faq,
    save_faq,
)
from ml.semantic.embeddings import upsert_embedding


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _find_item(items: list[dict[str, Any]], question: str) -> dict[str, Any] | None:
    target = (question or "").strip()

    for item in items:
        if (item.get("question") or "").strip() == target:
            return item

    return None


def register_use(company_id: str, matched_question: str | None) -> None:
    if not company_id or not matched_question:
        return

    items = load_faq(company_id)
    item = _find_item(items, matched_question)

    if not item:
        return

    item["uses"] = int(item.get("uses") or 0) + 1
    item["updated_at"] = _now()

    save_faq(company_id, items)


def upsert_faq_item(
    *,
    company_id: str,
    question: str,
    answer: str,
    intent: str = "general",
    quality_score: float = 0,
    source: str = "manual",
) -> dict[str, Any]:
    question = (question or "").strip()
    answer = (answer or "").strip()
    intent = (intent or "general").strip()

    if not company_id:
        raise ValueError("company_id é obrigatório.")
    if not question:
        raise ValueError("question é obrigatório.")
    if not answer:
        raise ValueError("answer é obrigatório.")

    items = load_faq(company_id)
    item = _find_item(items, question)

    if item is None:
        item = {
            "question": question,
            "uses": 0,
            "created_at": _now(),
        }
        items.append(item)

    item.update(
        {
            "question": question,
            "answer": answer,
            "intent": intent,
            "quality_score": float(quality_score or item.get("quality_score") or 0),
            "score": float(quality_score or item.get("score") or 0),
            "status": "active",
            "source": source,
            "updated_at": _now(),
        }
    )

    save_faq(company_id, items)
    reindex_faq_item(company_id=company_id, item=item)

    append_quality_event(
        company_id,
        {
            "type": "faq_upsert",
            "question": question,
            "intent": intent,
            "source": source,
            "quality_score": item.get("quality_score"),
        },
    )

    return item


def correct_faq_answer(
    *,
    company_id: str,
    question: str,
    corrected_answer: str,
    intent: str = "general",
    reason: str | None = None,
    reviewer: str | None = None,
) -> dict[str, Any]:
    item = upsert_faq_item(
        company_id=company_id,
        question=question,
        answer=corrected_answer,
        intent=intent,
        quality_score=1.0,
        source="correction",
    )

    append_correction(
        company_id,
        {
            "question": question,
            "corrected_answer": corrected_answer,
            "intent": intent,
            "reason": reason,
            "reviewer": reviewer,
            "faq_id": item.get("faq_id"),
        },
    )

    append_quality_event(
        company_id,
        {
            "type": "faq_correction",
            "question": question,
            "intent": intent,
            "reason": reason,
            "reviewer": reviewer,
            "quality_score": 1.0,
        },
    )

    return item


def reindex_faq_item(company_id: str, item: dict[str, Any]) -> None:
    question = (item.get("question") or "").strip()

    if not question:
        return

    upsert_embedding(
        company_id=company_id,
        namespace="faq",
        text=question,
        metadata={
            "answer": item.get("answer"),
            "intent": item.get("intent"),
            "uses": item.get("uses") or 0,
            "quality_score": item.get("quality_score") or item.get("score") or 0,
            "faq_id": item.get("faq_id"),
            "status": item.get("status") or "active",
        },
    )


def reindex_company_faq(company_id: str) -> dict[str, int]:
    items = load_faq(company_id)

    indexed = 0
    skipped = 0

    for item in items:
        if item.get("status") == "inactive":
            skipped += 1
            continue

        try:
            reindex_faq_item(company_id=company_id, item=item)
            indexed += 1
        except Exception:
            skipped += 1

    append_quality_event(
        company_id,
        {
            "type": "faq_reindex",
            "indexed": indexed,
            "skipped": skipped,
        },
    )

    return {
        "indexed": indexed,
        "skipped": skipped,
        "total": len(items),
    }
