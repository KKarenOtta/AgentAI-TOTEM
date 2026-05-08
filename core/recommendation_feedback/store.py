from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.persistence.jsonl_store import append_jsonl, read_jsonl, write_jsonl


EVENTS_PATH = Path("data/recommendation_feedback/events.jsonl")
WEIGHTS_PATH = Path("data/recommender/campaign_weights.json")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_recommendation_event(
    *,
    company_id: str,
    session_id: str | None,
    campaign_id: str | None,
    event_type: str,
    intent: str | None = None,
    score: float | None = None,
    reward: float | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "event_id": uuid4().hex,
        "timestamp": _now(),
        "company_id": company_id,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "event_type": event_type,
        "intent": intent,
        "score": score,
        "reward": reward,
        "payload": payload or {},
    }

    append_jsonl(EVENTS_PATH, event)
    return event


def load_recommendation_events(company_id: str | None = None) -> list[dict[str, Any]]:
    rows = read_jsonl(EVENTS_PATH)

    if company_id:
        return [row for row in rows if row.get("company_id") == company_id]

    return rows


def compute_reward(event_type: str, payload: dict[str, Any] | None = None) -> float:
    payload = payload or {}
    value = str(event_type or "").strip().lower()

    if value in {"conversion", "coupon_redeemed", "redeemed"}:
        return 1.0

    if value in {"lead_capture", "lead"}:
        return 0.65

    if value in {"click", "cta_click", "qr_open"}:
        return 0.35

    if value in {"impression", "shown"}:
        return 0.05

    if value in {"dismiss", "ignored", "abandoned"}:
        return -0.2

    if value in {"negative_nps", "complaint"}:
        return -0.5

    if payload.get("nps_score") is not None:
        score = int(payload.get("nps_score"))
        if score >= 9:
            return 0.5
        if score >= 7:
            return 0.1
        return -0.35

    return 0.0


def update_campaign_weight(
    *,
    company_id: str,
    campaign_id: str,
    reward: float,
    learning_rate: float = 0.08,
) -> dict[str, Any]:
    import json

    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if WEIGHTS_PATH.exists():
        try:
            data = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}

    data.setdefault("campaign_weights", {})
    weights = data["campaign_weights"]

    item = weights.get(campaign_id) or {
        "company_id": company_id,
        "campaign_id": campaign_id,
        "weight": 1.0,
        "interactions": 0,
        "reward_sum": 0.0,
        "last_reward": 0.0,
    }

    current = float(item.get("weight") or 1.0)
    next_weight = current + (float(reward) * learning_rate)
    next_weight = max(0.25, min(3.0, next_weight))

    item["company_id"] = company_id
    item["campaign_id"] = campaign_id
    item["weight"] = round(next_weight, 4)
    item["interactions"] = int(item.get("interactions") or 0) + 1
    item["reward_sum"] = round(float(item.get("reward_sum") or 0.0) + float(reward), 4)
    item["last_reward"] = round(float(reward), 4)
    item["updated_at"] = _now()

    weights[campaign_id] = item

    WEIGHTS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return item


def register_reward(
    *,
    company_id: str,
    session_id: str | None,
    campaign_id: str,
    event_type: str,
    intent: str | None = None,
    score: float | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reward = compute_reward(event_type, payload)

    event = log_recommendation_event(
        company_id=company_id,
        session_id=session_id,
        campaign_id=campaign_id,
        event_type=event_type,
        intent=intent,
        score=score,
        reward=reward,
        payload=payload or {},
    )

    weight = update_campaign_weight(
        company_id=company_id,
        campaign_id=campaign_id,
        reward=reward,
    )

    return {
        "event": event,
        "weight": weight,
    }


def build_recommendation_summary(company_id: str) -> dict[str, Any]:
    rows = load_recommendation_events(company_id)

    by_campaign: dict[str, dict[str, Any]] = {}

    for row in rows:
        campaign_id = row.get("campaign_id") or "unknown"

        item = by_campaign.setdefault(
            campaign_id,
            {
                "campaign_id": campaign_id,
                "events": 0,
                "reward_sum": 0.0,
                "conversions": 0,
                "clicks": 0,
                "impressions": 0,
            },
        )

        item["events"] += 1
        item["reward_sum"] += float(row.get("reward") or 0)

        event_type = str(row.get("event_type") or "").lower()

        if event_type in {"conversion", "coupon_redeemed", "redeemed"}:
            item["conversions"] += 1
        elif event_type in {"click", "cta_click", "qr_open"}:
            item["clicks"] += 1
        elif event_type in {"impression", "shown"}:
            item["impressions"] += 1

    result = []

    for item in by_campaign.values():
        item["reward_sum"] = round(item["reward_sum"], 4)
        item["conversion_rate"] = round(
            (item["conversions"] / item["impressions"]) * 100,
            2,
        ) if item["impressions"] else 0.0
        result.append(item)

    result.sort(key=lambda row: row["reward_sum"], reverse=True)

    return {
        "company_id": company_id,
        "campaigns": result,
        "events": len(rows),
    }
