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

    # 1) prioridade base (se existir)
    priority = float(campaign.get("priority", 1.0))
    score += w["base_priority"] * priority
    why.append(f"prioridade={priority}")

    # 2) match por intenção
    tags = set((campaign.get("tags") or []))
    if intent in tags:
        score += w["intent_match"]
        why.append("match_intent")

    # 3) returning
    if profile and profile.get("customer_type") == "returning":
        if campaign.get("returning_only") is True or "returning" in tags:
            score += w["returning_bonus"]
            why.append("returning")

    # 4) faixa etária (se tiver)
    if profile and profile.get("age_range") and campaign.get("age_ranges"):
        if profile["age_range"] in campaign["age_ranges"]:
            score += w["age_match"]
            why.append("age_match")

    return round(score, 3), ", ".join(why)