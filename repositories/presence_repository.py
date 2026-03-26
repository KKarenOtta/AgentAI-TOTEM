from __future__ import annotations

from time import time
from typing import Any


class PresenceRepository:
    def __init__(self) -> None:
        self._state: dict[tuple[str, str], dict[str, Any]] = {}

    def set_present(self, company_id: str, device_id: str) -> dict[str, Any]:
        key = (company_id, device_id)
        state = {
            "company_id": company_id,
            "device_id": device_id,
            "present": True,
            "last_seen_ts": time(),
        }
        self._state[key] = state
        return state

    def heartbeat(self, company_id: str, device_id: str) -> dict[str, Any]:
        return self.set_present(company_id=company_id, device_id=device_id)

    def clear(self, company_id: str, device_id: str) -> dict[str, Any]:
        key = (company_id, device_id)
        state = {
            "company_id": company_id,
            "device_id": device_id,
            "present": False,
            "last_seen_ts": time(),
        }
        self._state[key] = state
        return state

    def get(self, company_id: str, device_id: str) -> dict[str, Any] | None:
        return self._state.get((company_id, device_id))
