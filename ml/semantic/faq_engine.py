from __future__ import annotations

from typing import Any

from core.faq.ranking import rank
from core.faq.store import load_faq
from ml.semantic.embeddings import embed, cosine


class FAQEngine:
    def search(
        self,
        company_id: str,
        query: str,
        intent: str | None = None,
        min_score: float = 0.5,
    ) -> tuple[str, float, str | None]:
        query = (query or "").strip()

        if not company_id or not query:
            return "", 0.0, None

        items = rank(load_faq(company_id))

        if not items:
            return "", 0.0, None

        query_embedding = embed(query)

        best_item: dict[str, Any] | None = None
        best_score = 0.0

        for item in items:
            question = (item.get("question") or "").strip()
            answer = (item.get("answer") or "").strip()

            if not question or not answer:
                continue

            item_embedding = item.get("embedding")
            if item_embedding is None:
                item_embedding = embed(question)

            semantic_score = cosine(query_embedding, item_embedding)
            usage_weight = min(float(item.get("uses") or 0) * 0.01, 0.15)
            quality_weight = min(float(item.get("score") or 0) * 0.01, 0.20)

            final_score = semantic_score + usage_weight + quality_weight

            if intent and item.get("intent") == intent:
                final_score += 0.05

            if final_score > best_score:
                best_score = final_score
                best_item = item

        if not best_item or best_score < min_score:
            return "", round(best_score, 4), None

        return (
            (best_item.get("answer") or "").strip(),
            round(best_score, 4),
            (best_item.get("question") or "").strip(),
        )
