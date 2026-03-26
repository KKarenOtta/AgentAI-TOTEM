from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class CompanyRepository:
    def __init__(self, path: str = "data/companies.json") -> None:
        self.path = Path(path)

    def list_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        data = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []

    def get_by_id(self, company_id: str) -> dict[str, Any] | None:
        for item in self.list_all():
            if item.get("company_id") == company_id or item.get("id") == company_id:
                return item
        return None
