from typing import List, Dict, Any
from datetime import date
import uuid

# store simples em memória (dev)
_STORE: Dict[str, List[Dict[str, Any]]] = {}

def _seed(company_id: str):
    if company_id not in _STORE:
        _STORE[company_id] = [{
            "campaign_id": "CAMP-001",
            "name": "Promo Verão",
            "channel": "instagram",
            "objective": "leads",
            "status": "active",
            "target_segments": ["18-24", "25-34"],
            "start_date": str(date.today()),
        }]

def list_campaigns(company_id: str) -> List[Dict[str, Any]]:
    _seed(company_id)
    return _STORE[company_id]

def get_active_campaigns(company_id: str) -> List[Dict[str, Any]]:
    _seed(company_id)
    return [c for c in _STORE[company_id] if c.get("status") == "active"]

def create_campaign(company_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _seed(company_id)
    c = dict(payload)
    c["campaign_id"] = c.get("campaign_id") or f"CAMP-{uuid.uuid4().hex[:6].upper()}"
    c.setdefault("status", "active")
    c.setdefault("start_date", str(date.today()))
    _STORE[company_id].append(c)
    return c

def update_campaign(company_id: str, campaign_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _seed(company_id)
    for c in _STORE[company_id]:
        if c["campaign_id"] == campaign_id:
            c.update(payload)
            return c
    raise KeyError("campaign_id not found")

def delete_campaign(company_id: str, campaign_id: str) -> None:
    _seed(company_id)
    _STORE[company_id] = [c for c in _STORE[company_id] if c["campaign_id"] != campaign_id]