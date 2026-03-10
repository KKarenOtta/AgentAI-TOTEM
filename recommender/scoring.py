from __future__ import annotations

def infer_intent(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["promo", "oferta", "desconto", "promoções"]):
        return "promotions"
    if any(k in t for k in ["horário", "aberto", "fecha", "funciona"]):
        return "hours"
    if any(k in t for k in ["troca", "devolução", "reembolso"]):
        return "returns"
    return "general"


DEFAULT_WEIGHTS = {
    "base_priority": 1.0,
    "intent_match": 2.0,
    "returning_bonus": 0.7,
    "age_match": 0.4,
}


def score_campaign(campaign: dict, profile: dict | None, intent: str, weights: dict | None = None) -> tuple[float, str]:
    w = weights or DEFAULT_WEIGHTS

    score = 0.0
    why = []

    priority = float(campaign.get("priority", 1.0))
    score += w["base_priority"] * priority
    why.append(f"prioridade={priority}")

    tags = set(campaign.get("tags") or [])
    if intent in tags:
        score += w["intent_match"]
        why.append("match_intent")

    if profile and profile.get("customer_type") == "returning":
        if campaign.get("returning_only") is True or "returning" in tags:
            score += w["returning_bonus"]
            why.append("returning")

    campaign_age_ranges = campaign.get("age_ranges") or campaign.get("target_segments") or []
    user_age_range = profile.get("age_range") if profile else None

    if user_age_range and campaign_age_ranges:
        if user_age_range in campaign_age_ranges:
            score += w["age_match"]
            why.append("age_match")

    return round(score, 3), ", ".join(why)