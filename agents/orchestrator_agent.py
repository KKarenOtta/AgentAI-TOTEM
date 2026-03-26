from __future__ import annotations

from typing import Any

from agents.intent_agent import IntentAgent
from agents.recommendation_agent import RecommendationAgent
from agents.response_agent import ResponseAgent
from agents.translation_agent import TranslationAgent
from repositories.campaign_repository import CampaignRepository


class OrchestratorAgent:
    def __init__(self) -> None:
        self.intent_agent = IntentAgent()
        self.recommendation_agent = RecommendationAgent()
        self.response_agent = ResponseAgent()
        self.translation_agent = TranslationAgent()
        self.campaign_repository = CampaignRepository()

    def run(
        self,
        *,
        company_id: str,
        message: str,
        target_language: str | None = None,
    ) -> dict[str, Any]:
        intent = self.intent_agent.detect(message)
        campaigns = self.campaign_repository.list_by_company(company_id=company_id)
        recommendations = self.recommendation_agent.rank(
            campaigns=campaigns,
            intent=intent.label,
            company_id=company_id,
        )
        answer_text = self.response_agent.generate_fallback(intent=intent.label)

        translated_text = None
        if target_language:
            translated_text = self.translation_agent.translate(
                text=answer_text,
                target_language=target_language,
            )

        return {
            "intent": intent.label,
            "intent_confidence": intent.confidence,
            "answer_text": answer_text,
            "translated_text": translated_text,
            "recommendations": recommendations,
        }
