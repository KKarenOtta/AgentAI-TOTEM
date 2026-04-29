from __future__ import annotations

from typing import Any

from core.faq.ranking import rank
from core.faq.store import load_faq
from ml.semantic.embeddings import cosine, embed, search_embeddings


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

        indexed_answer = self._search_persistent_embeddings(
            company_id=company_id,
            query=query,
            intent=intent,
            min_score=min_score,
        )

        if indexed_answer:
            return indexed_answer

        return self._search_runtime_faq(
            company_id=company_id,
            query=query,
            intent=intent,
            min_score=min_score,
        )

    def _search_persistent_embeddings(
        self,
        company_id: str,
        query: str,
        intent: str | None,
        min_score: float,
    ) -> tuple[str, float, str | None] | None:
        results = search_embeddings(
            company_id=company_id,
            namespace="faq",
            query=query,
            top_k=5,
            min_score=max(0.0, min_score - 0.10),
        )

        best_result: dict[str, Any] | None = None
        best_score = 0.0

        for result in results:
            metadata = result.get("metadata") or {}
            answer = (metadata.get("answer") or "").strip()

            if not answer:
                continue

            score = float(result.get("score") or 0)

            if intent and metadata.get("intent") == intent:
                score += 0.05

            uses = float(metadata.get("uses") or 0)
            quality_score = float(metadata.get("quality_score") or 0)

            score += min(uses * 0.01, 0.15)
            score += min(quality_score * 0.01, 0.20)

            if score > best_score:
                best_score = score
                best_result = result

        if not best_result or best_score < min_score:
            return None

        metadata = best_result.get("metadata") or {}

        return (
            (metadata.get("answer") or "").strip(),
            round(best_score, 4),
            (best_result.get("text") or "").strip(),
        )

    def _search_runtime_faq(
        self,
        company_id: str,
        query: str,
        intent: str | None,
        min_score: float,
    ) -> tuple[str, float, str | None]:
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
