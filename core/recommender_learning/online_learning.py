from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

WEIGHTS_PATH = Path("data/recommender/campaign_weights.json")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_weights() -> dict[str, Any]:
    if not WEIGHTS_PATH.exists():
        return {"campaign_weights": {}}

    try:
        return json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"campaign_weights": {}}


def save_weights(data: dict[str, Any]) -> None:
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    WEIGHTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_campaign_reward(company_id: str, campaign_id: str, reward: float, reason: str = "") -> dict[str, Any]:
    data = load_weights()
    weights = data.setdefault("campaign_weights", {})

    item = weights.setdefault(
        campaign_id,
        {
            "company_id": company_id,
            "weight": 1.0,
            "events": 0,
            "reward_sum": 0.0,
            "last_reason": "",
        },
    )

    item["company_id"] = company_id
    item["events"] = int(item.get("events") or 0) + 1
    item["reward_sum"] = round(float(item.get("reward_sum") or 0) + float(reward), 4)
    item["weight"] = round(max(0.1, min(5.0, float(item.get("weight") or 1.0) + float(reward) * 0.1)), 4)
    item["last_reason"] = reason
    item["updated_at"] = _now()

    save_weights(data)
    return item


def personalize_score(base_score: float, campaign_id: str, segment: str | None = None) -> float:
    data = load_weights()
    item = (data.get("campaign_weights") or {}).get(campaign_id) or {}
    weight = float(item.get("weight") or 1.0)

    segment_bonus = 0.05 if segment else 0.0
    return round(float(base_score) * weight + segment_bonus, 4)
