from __future__ import annotations

from typing import Any


class RecommendationAgent:
    def rank(
        self,
        campaigns: list[dict[str, Any]],
        intent: str,
        company_id: str | None = None,
    ) -> list[dict[str, Any]]:
        ranked: list[tuple[int, dict[str, Any]]] = []

        for campaign in campaigns:
            if campaign.get("status") not in {"active", "published"}:
                continue

            score = 0

            if company_id and campaign.get("company_id") == company_id:
                score += 4

            if campaign.get("channel") in {"totem", "kiosk", "onsite"}:
                score += 3

            target_intents = campaign.get("target_intents") or campaign.get("target_segments") or []
            if isinstance(target_intents, str):
                target_intents = [target_intents]

            if intent in target_intents:
                score += 5

            if campaign.get("priority") == "high":
                score += 2

            ranked.append((score, campaign))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in ranked[:3]]
