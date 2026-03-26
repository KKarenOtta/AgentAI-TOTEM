from __future__ import annotations

import requests


class PresenceSender:
    def __init__(self, api_base_url: str) -> None:
        self.api_base_url = api_base_url.rstrip("/")

    def _post(self, path: str, company_id: str, device_id: str) -> None:
        response = requests.post(
            f"{self.api_base_url}/{path}",
            json={
                "company_id": company_id,
                "device_id": device_id,
            },
            timeout=5,
        )
        response.raise_for_status()

    def trigger(self, company_id: str, device_id: str) -> None:
        self._post("presence/trigger", company_id, device_id)

    def heartbeat(self, company_id: str, device_id: str) -> None:
        self._post("presence/heartbeat", company_id, device_id)

    def clear(self, company_id: str, device_id: str) -> None:
        self._post("presence/clear", company_id, device_id)
