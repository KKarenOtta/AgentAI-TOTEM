from __future__ import annotations

import os
import threading
import time
from typing import Any


class PresenceRepository:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: dict[tuple[str, str], dict[str, Any]] = {}
        self._active_sessions: dict[tuple[str, str], dict[str, Any]] = {}

        self.debounce_seconds = float(os.getenv("PRESENCE_DEBOUNCE_SECONDS", "5"))
        self.cooldown_seconds = float(os.getenv("PRESENCE_COOLDOWN_SECONDS", "8"))
        self.active_session_ttl_seconds = float(os.getenv("PRESENCE_ACTIVE_SESSION_TTL_SECONDS", "600"))

    def set_present(
        self,
        company_id: str,
        device_id: str,
        session_id: str,
        attributes: dict[str, Any] | None = None,
        sensor_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        key = self._key(company_id, device_id)

        with self._lock:
            previous = self._state.get(key) or {}
            active = self._active_sessions.get(key) or {}

            previous_seen = float(previous.get("last_seen_ts") or 0)
            active_started = float(active.get("started_ts") or 0)
            active_session_id = active.get("session_id")

            has_active_session = (
                bool(active_session_id)
                and now - active_started < self.active_session_ttl_seconds
            )

            is_debounce = previous_seen > 0 and now - previous_seen < self.debounce_seconds
            is_duplicate = has_active_session and bool(active_session_id)

            if has_active_session:
                session_id = str(active_session_id)
                is_new_session = False
            else:
                self._active_sessions[key] = {
                    "company_id": company_id,
                    "device_id": device_id,
                    "session_id": session_id,
                    "started_ts": now,
                    "last_seen_ts": now,
                }
                is_new_session = True

            if key in self._active_sessions:
                self._active_sessions[key]["last_seen_ts"] = now

            state = {
                "company_id": company_id,
                "device_id": device_id,
                "session_id": session_id,
                "present": True,
                "validated": bool((attributes or {}).get("human_validated", True)),
                "last_seen_ts": now,
                "attributes": attributes or {},
                "sensor_payload": sensor_payload or {},
                "is_new_session": is_new_session,
                "is_duplicate": bool(is_duplicate or is_debounce),
                "debounced": bool(is_debounce),
                "reason": "new_session" if is_new_session else "active_session_reused",
            }

            self._state[key] = state
            return dict(state)

    def heartbeat(self, company_id: str, device_id: str) -> dict[str, Any]:
        now = time.time()
        key = self._key(company_id, device_id)

        with self._lock:
            previous = self._state.get(key) or {}
            active = self._active_sessions.get(key) or {}

            session_id = active.get("session_id") or previous.get("session_id")

            if key in self._active_sessions:
                self._active_sessions[key]["last_seen_ts"] = now

            state = {
                "company_id": company_id,
                "device_id": device_id,
                "session_id": session_id,
                "present": bool(session_id),
                "last_seen_ts": now,
                "attributes": previous.get("attributes") or {},
                "sensor_payload": previous.get("sensor_payload") or {},
                "is_new_session": False,
                "is_duplicate": True,
                "debounced": False,
                "reason": "heartbeat",
            }

            self._state[key] = state
            return dict(state)

    def clear(self, company_id: str, device_id: str) -> dict[str, Any]:
        now = time.time()
        key = self._key(company_id, device_id)

        with self._lock:
            active = self._active_sessions.pop(key, {}) or {}
            session_id = active.get("session_id")

            state = {
                "company_id": company_id,
                "device_id": device_id,
                "session_id": session_id,
                "present": False,
                "last_seen_ts": now,
                "attributes": {},
                "sensor_payload": {},
                "is_new_session": False,
                "is_duplicate": False,
                "debounced": False,
                "reason": "cleared",
            }

            self._state[key] = state
            return dict(state)

    def get(self, company_id: str, device_id: str) -> dict[str, Any] | None:
        with self._lock:
            state = self._state.get(self._key(company_id, device_id))
            return dict(state) if state else None

    def active_session(self, company_id: str, device_id: str) -> str | None:
        now = time.time()
        key = self._key(company_id, device_id)

        with self._lock:
            active = self._active_sessions.get(key)
            if not active:
                return None

            started = float(active.get("started_ts") or 0)
            if now - started >= self.active_session_ttl_seconds:
                self._active_sessions.pop(key, None)
                return None

            return active.get("session_id")

    @staticmethod
    def _key(company_id: str, device_id: str) -> tuple[str, str]:
        return company_id.strip(), device_id.strip()
