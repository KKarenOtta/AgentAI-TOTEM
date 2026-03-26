from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
import json
import os
import threading
import uuid


DEFAULT_PATH = os.getenv("CAMPAIGNS_DB_PATH", "data/campaigns.json")
_LOCK = threading.Lock()


def _ensure_file(path: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        file_path.write_text("{}", encoding="utf-8")


def _load_all(path: str = DEFAULT_PATH) -> dict[str, list[dict[str, Any]]]:
    _ensure_file(path)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def _save_all(store: dict[str, list[dict[str, Any]]], path: str = DEFAULT_PATH) -> None:
    _ensure_file(path)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _normalize_campaign(company_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    campaign = dict(payload or {})

    campaign["company_id"] = company_id
    campaign["campaign_id"] = campaign.get("campaign_id") or f"CAMP-{uuid.uuid4().hex[:6].upper()}"
    campaign["name"] = (campaign.get("name") or "Campanha").strip()
    campaign["description"] = (campaign.get("description") or "").strip()
    campaign["channel"] = (campaign.get("channel") or "totem").strip()
    campaign["status"] = (campaign.get("status") or "active").strip()
    campaign["objective"] = (campaign.get("objective") or "conversion").strip()
    campaign["cta_label"] = (campaign.get("cta_label") or "Quero meu desconto").strip()
    campaign["discount_type"] = (campaign.get("discount_type") or "percent").strip()
    campaign["coupon_code"] = (campaign.get("coupon_code") or "").strip()
    campaign["landing_url"] = (campaign.get("landing_url") or "").strip()
    campaign["media_image"] = (campaign.get("media_image") or "").strip()
    campaign["qr_mode"] = (campaign.get("qr_mode") or "coupon").strip()
    campaign["priority"] = campaign.get("priority") or "normal"
    campaign["start_date"] = campaign.get("start_date") or str(date.today())
    campaign["end_date"] = campaign.get("end_date") or None

    try:
        campaign["discount_value"] = float(campaign.get("discount_value") or 0)
    except Exception:
        campaign["discount_value"] = 0.0

    target_intents = campaign.get("target_intents") or []
    if isinstance(target_intents, str):
        target_intents = [item.strip() for item in target_intents.split(",") if item.strip()]
    campaign["target_intents"] = target_intents

    target_segments = campaign.get("target_segments") or campaign.get("age_ranges") or []
    if isinstance(target_segments, str):
        target_segments = [item.strip() for item in target_segments.split(",") if item.strip()]
    campaign["target_segments"] = target_segments

    tags = campaign.get("tags") or []
    if isinstance(tags, str):
        tags = [item.strip() for item in tags.split(",") if item.strip()]

    merged_tags = set(tags)
    for item in campaign["target_intents"]:
        merged_tags.add(item)
    campaign["tags"] = sorted(merged_tags)

    return campaign


def _seed_company(store: dict[str, list[dict[str, Any]]], company_id: str) -> None:
    if company_id not in store or not isinstance(store.get(company_id), list):
        store[company_id] = []

    if store[company_id]:
        return

    store[company_id].append(
        _normalize_campaign(
            company_id,
            {
                "campaign_id": "CAMP-001",
                "name": "Boas-vindas no Totem",
                "description": "Ganhe 10% OFF na primeira compra feita hoje.",
                "channel": "totem",
                "objective": "conversion",
                "status": "active",
                "target_intents": ["promotion", "product"],
                "target_segments": ["18-24", "25-34", "35-44"],
                "cta_label": "Quero meu desconto",
                "discount_type": "percent",
                "discount_value": 10,
                "coupon_code": "BEMVINDO10",
                "priority": "high",
                "qr_mode": "coupon",
            },
        )
    )


def list_campaigns(company_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)
        _save_all(store)
        return store[company_id]


def get_active_campaigns(company_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)
        _save_all(store)

        return [
            campaign
            for campaign in store[company_id]
            if campaign.get("status") == "active"
        ]


def create_campaign(company_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)

        campaign = _normalize_campaign(company_id, payload)
        store[company_id].append(campaign)
        _save_all(store)

        return campaign


def update_campaign(company_id: str, campaign_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)

        for index, existing in enumerate(store[company_id]):
            if existing.get("campaign_id") == campaign_id:
                merged = dict(existing)
                merged.update(payload or {})
                normalized = _normalize_campaign(company_id, merged)
                normalized["campaign_id"] = campaign_id
                store[company_id][index] = normalized
                _save_all(store)
                return normalized

        raise KeyError("campaign_id not found")


def delete_campaign(company_id: str, campaign_id: str) -> None:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)

        store[company_id] = [
            campaign
            for campaign in store[company_id]
            if campaign.get("campaign_id") != campaign_id
        ]
        _save_all(store)
