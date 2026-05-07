from __future__ import annotations

from typing import Any

from recommender.scoring import score_campaign


def recommend_actions(
    profile: dict[str, Any] | None,
    active_campaigns: list[dict[str, Any]] | None,
    intent: str | None = None,
    top_k: int = 3,
    company_id: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    intent = intent or "general"

    scored = []
    for campaign in active_campaigns or []:
        score, why = score_campaign(
            campaign=campaign,
            profile=profile,
            intent=intent,
            company_id=company_id,
        )
        scored.append((score, campaign, why))

    scored.sort(key=lambda item: item[0], reverse=True)

    top_actions = []
    for score, campaign, why in scored[:top_k]:
        top_actions.append(
            {
                "type": "campaign",
                "campaign_id": campaign.get("campaign_id") or campaign.get("id") or campaign.get("code"),
                "title": campaign.get("title") or campaign.get("name") or "Campanha",
                "description": campaign.get("description") or "",
                "cta_label": campaign.get("cta_label") or campaign.get("cta") or "Quero meu desconto",
                "action": campaign.get("cta_label") or campaign.get("cta") or "Quero meu desconto",
                "media_image": campaign.get("media_image") or "",
                "coupon_code": campaign.get("coupon_code") or "",
                "discount_type": campaign.get("discount_type") or "",
                "discount_value": campaign.get("discount_value") or 0,
                "landing_url": campaign.get("landing_url") or "",
                "score": score,
                "why": why,
            }
        )

    if not top_actions:
        top_actions = [
            {
                "type": "generic",
                "campaign_id": None,
                "title": "Sem campanha elegível",
                "description": "Nenhuma campanha ativa compatível com a intenção atual.",
                "cta_label": "Explorar opções",
                "action": "Explorar opções",
                "media_image": "",
                "coupon_code": "",
                "discount_type": "",
                "discount_value": 0,
                "landing_url": "",
                "score": 0.1,
                "why": "Sem campanhas elegíveis; coletar intenção melhora recomendação.",
            }
        ]

    return {"top_actions": top_actions}
