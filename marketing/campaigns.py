from typing import List, Dict, Any
from datetime import date
import uuid
import json
import os
import threading

# Persistência em JSON (por company_id)
DEFAULT_PATH = os.getenv("CAMPAIGNS_DB_PATH", "data/campaigns.json")

_LOCK = threading.Lock()

def _ensure_file(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)

def _load_all(path: str = DEFAULT_PATH) -> Dict[str, List[Dict[str, Any]]]:
    _ensure_file(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # garantia de tipo
        return data if isinstance(data, dict) else {}

def _save_all(store: Dict[str, List[Dict[str, Any]]], path: str = DEFAULT_PATH) -> None:
    _ensure_file(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)

def _seed_company(store: Dict[str, List[Dict[str, Any]]], company_id: str) -> None:
    """
    Seed apenas se a empresa ainda não tiver campanhas.
    """
    if company_id not in store or not isinstance(store.get(company_id), list):
        store[company_id] = []

    if len(store[company_id]) == 0:
        store[company_id].append({
            "campaign_id": "CAMP-001",
            "name": "Promo Verão",
            "channel": "instagram",
            "objective": "leads",
            "status": "active",
            "target_segments": ["18-24", "25-34"],
            "start_date": str(date.today()),
            # opcional: "end_date": None,
            # opcional: "priority": 1,
        })

def list_campaigns(company_id: str) -> List[Dict[str, Any]]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)
        _save_all(store)
        return store[company_id]

def get_active_campaigns(company_id: str) -> List[Dict[str, Any]]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)
        _save_all(store)
        return [c for c in store[company_id] if c.get("status") == "active"]

def create_campaign(company_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)

        c = dict(payload or {})
        c["campaign_id"] = c.get("campaign_id") or f"CAMP-{uuid.uuid4().hex[:6].upper()}"
        c.setdefault("status", "active")
        c.setdefault("start_date", str(date.today()))

        store[company_id].append(c)
        _save_all(store)
        return c

def update_campaign(company_id: str, campaign_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)

        for c in store[company_id]:
            if c.get("campaign_id") == campaign_id:
                c.update(payload or {})
                _save_all(store)
                return c
        raise KeyError("campaign_id not found")

def delete_campaign(company_id: str, campaign_id: str) -> None:
    with _LOCK:
        store = _load_all()
        _seed_company(store, company_id)

        store[company_id] = [c for c in store[company_id] if c.get("campaign_id") != campaign_id]
        _save_all(store)