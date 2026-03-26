from __future__ import annotations

from repositories.presence_repository import PresenceRepository


_presence_repo = PresenceRepository()


class PresenceService:
    def trigger(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.set_present(company_id=company_id, device_id=device_id)
        self._publish(company_id=company_id, event="presence_triggered", payload=state)
        return state

    def heartbeat(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.heartbeat(company_id=company_id, device_id=device_id)
        self._publish(company_id=company_id, event="presence_heartbeat", payload=state)
        return state

    def clear(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.clear(company_id=company_id, device_id=device_id)
        self._publish(company_id=company_id, event="presence_cleared", payload=state)
        return state

    @staticmethod
    def _publish(company_id: str, event: str, payload: dict) -> None:
        try:
            from services.realtime.event_bus import publish  # type: ignore
            publish(company_id=company_id, event=event, payload=payload)
        except Exception:
            return
