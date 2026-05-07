from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ml.business.predict import predict_conversion_score


WEIGHTS_PATH = Path("data/recommender/campaign_weights.json")


def infer_intent(text: str) -> str:
    value = (text or "").strip().lower()

    if any(term in value for term in ["promo", "promoção", "promoções", "oferta", "desconto", "cupom"]):
        return "promotion"

    if any(term in value for term in ["produto", "produtos", "comprar", "item", "recomende"]):
        return "product"

    if any(term in value for term in ["ajuda", "suporte", "atendimento", "problema", "resolver"]):
        return "support"

    if any(term in value for term in ["horário", "aberto", "fecha", "funciona"]):
        return "hours"

    if any(term in value for term in ["troca", "devolução", "reembolso"]):
        return "returns"

    if any(term in value for term in ["criança", "crianças", "infantil", "família", "familia", "bebê", "bebe"]):
        return "family"

    return "general"


def _priority_to_number(priority: object) -> float:
    value = str(priority or "normal").strip().lower()

    if value == "high":
        return 1.0

    if value == "normal":
        return 0.5

    if value == "low":
        return 0.15

    try:
        return float(value)
    except Exception:
        return 0.5


def _load_campaign_weights() -> dict[str, Any]:
    if not WEIGHTS_PATH.exists():
        return {}

    try:
        data = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    weights = data.get("campaign_weights") or {}
    return weights if isinstance(weights, dict) else {}


def _campaign_learning_weight(campaign_id: str | None) -> tuple[float, str]:
    if not campaign_id:
        return 0.0, "learning=0.00"

    weights = _load_campaign_weights()
    item = weights.get(campaign_id) or {}

    weight = float(item.get("weight") or 1.0)
    normalized = max(0.0, min(weight - 1.0, 2.0))

    return normalized, f"learning={round(normalized, 2)}"


def _ml_conversion_weight(company_id: str | None, campaign: dict[str, Any]) -> tuple[float, str]:
    if not company_id:
        return 0.0, "ml_conversion=0.00"

    try:
        probability = predict_conversion_score(company_id, campaign)
    except Exception:
        probability = 0.0

    probability = max(0.0, min(float(probability or 0.0), 1.0))
    weighted_score = probability * 1.25

    return weighted_score, f"ml_conversion={round(probability, 4)}"


def score_campaign(
    campaign: dict[str, Any],
    profile: dict[str, Any] | None,
    intent: str | None = None,
    company_id: str | None = None,
) -> tuple[float, str]:
    profile = profile or {}
    intent = intent or "general"

    why = []
    score = 0.0

    priority_score = _priority_to_number(campaign.get("priority"))
    score += priority_score
    why.append(f"priority={round(priority_score, 2)}")

    channel = str(campaign.get("channel") or "").strip().lower()
    if channel in {"totem", "kiosk", "onsite", ""}:
        score += 0.5
        why.append("channel_match=0.50")

    target_intents = campaign.get("target_intents") or campaign.get("tags") or []
    if isinstance(target_intents, str):
        target_intents = [item.strip() for item in target_intents.split(",") if item.strip()]

    merged_intents = {str(item).strip().lower() for item in target_intents if str(item).strip()}

    if intent and intent != "general" and intent in merged_intents:
        score += 0.75
        why.append("intent_match=0.75")
    elif not merged_intents:
        score += 0.15
        why.append("intent_open=0.15")

    user_segment = str(profile.get("customer_type") or profile.get("segment") or "").strip().lower()
    target_segments = campaign.get("target_segments") or []
    if isinstance(target_segments, str):
        target_segments = [item.strip() for item in target_segments.split(",") if item.strip()]

    if user_segment and user_segment in {str(item).strip().lower() for item in target_segments}:
        score += 0.5
        why.append("segment_match=0.50")

    user_age_range = str(profile.get("age_range") or "").strip()
    campaign_age_ranges = campaign.get("age_ranges") or campaign.get("target_age_ranges") or []
    if isinstance(campaign_age_ranges, str):
        campaign_age_ranges = [item.strip() for item in campaign_age_ranges.split(",") if item.strip()]

    if user_age_range and user_age_range in campaign_age_ranges:
        score += 0.35
        why.append("age_match=0.35")

    if profile.get("returning") and campaign.get("returning_only"):
        score += 0.35
        why.append("returning_bonus=0.35")

    campaign_id = campaign.get("campaign_id") or campaign.get("id") or campaign.get("code")
    learning_score, learning_reason = _campaign_learning_weight(campaign_id)
    score += learning_score
    why.append(learning_reason)

    ml_score, ml_reason = _ml_conversion_weight(company_id, campaign)
    score += ml_score
    why.append(ml_reason)

    return round(score, 4), ", ".join(why)
