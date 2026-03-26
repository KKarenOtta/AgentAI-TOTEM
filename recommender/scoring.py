from __future__ import annotations


DEFAULT_WEIGHTS = {
    "base_priority": 1.0,
    "intent_match": 2.5,
    "channel_match": 1.0,
    "segment_match": 0.8,
    "age_match": 0.5,
    "returning_bonus": 0.7,
}


def infer_intent(text: str) -> str:
    t = (text or "").strip().lower()

    if any(k in t for k in ["promo", "promoção", "promoções", "oferta", "desconto", "cupom"]):
        return "promotion"

    if any(k in t for k in ["produto", "produtos", "comprar", "item", "recomende"]):
        return "product"

    if any(k in t for k in ["ajuda", "suporte", "atendimento", "problema", "resolver"]):
        return "support"

    if any(k in t for k in ["horário", "aberto", "fecha", "funciona"]):
        return "hours"

    if any(k in t for k in ["troca", "devolução", "reembolso"]):
        return "returns"

    return "general"


def _priority_to_number(priority: object) -> float:
    if isinstance(priority, (int, float)):
        return float(priority)

    text = str(priority or "").strip().lower()

    if text == "high":
        return 2.0
    if text == "normal":
        return 1.0
    if text == "low":
        return 0.5

    return 1.0


def score_campaign(
    campaign: dict,
    profile: dict | None,
    intent: str,
    weights: dict | None = None,
) -> tuple[float, str]:
    w = weights or DEFAULT_WEIGHTS

    score = 0.0
    why: list[str] = []

    priority = _priority_to_number(campaign.get("priority"))
    score += w["base_priority"] * priority
    why.append(f"priority={priority}")

    tags = set(campaign.get("tags") or [])
    target_intents = set(campaign.get("target_intents") or [])
    merged_intents = tags.union(target_intents)

    if intent in merged_intents:
        score += w["intent_match"]
        why.append("intent_match")

    channel = str(campaign.get("channel") or "").strip().lower()
    if channel in {"totem", "kiosk", "onsite"}:
        score += w["channel_match"]
        why.append("channel_match")

    if profile:
        user_segment = profile.get("segment") or profile.get("customer_type")
        target_segments = campaign.get("target_segments") or []

        if user_segment and user_segment in target_segments:
            score += w["segment_match"]
            why.append("segment_match")

        user_age_range = profile.get("age_range")
        if user_age_range and target_segments and user_age_range in target_segments:
            score += w["age_match"]
            why.append("age_match")

        if user_segment == "returning" and campaign.get("returning_only") is True:
            score += w["returning_bonus"]
            why.append("returning_bonus")

    return round(score, 3), ", ".join(why)
