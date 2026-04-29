from __future__ import annotations

from core.faq.store import load_faq, save_faq


def register_use(company_id: str, matched_question: str | None) -> None:
    if not company_id or not matched_question:
        return

    items = load_faq(company_id)

    changed = False

    for item in items:
        if (item.get("question") or "").strip() == matched_question.strip():
            item["uses"] = int(item.get("uses") or 0) + 1
            changed = True
            break

    if changed:
        save_faq(company_id, items)
