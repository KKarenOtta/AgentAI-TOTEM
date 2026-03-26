from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CampaignRepository:
    def __init__(self, path: str = "data/campaigns.json") -> None:
        self.path = Path(path)

    def list_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        data = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []

    def list_by_company(self, company_id: str) -> list[dict[str, Any]]:
        return [
            campaign
            for campaign in self.list_all()
            if campaign.get("company_id") == company_id
        ]
