from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _key(session_id: str) -> str:
    return f"totem:session:{session_id}"


def _save(session_id: str, data: dict[str, Any]) -> None:
    r.setex(_key(session_id), SESSION_TTL_SECONDS, json.dumps(data, ensure_ascii=False))


def get_or_create_session(company_id: str, session_id: str, profile: dict | None = None) -> dict[str, Any]:
    existing = get_session(session_id)

    if existing:
        if profile is not None:
            existing["profile"] = profile
            _save(session_id, existing)
        return existing

    data = {
        "session_id": session_id,
        "company_id": company_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "turn": 0,
        "profile": profile,
        "history": [],
        "last_intent": None,
        "last_recommendations": {},
    }

    _save(session_id, data)
    return data


def get_session(session_id: str) -> dict[str, Any] | None:
    raw = r.get(_key(session_id))
    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def increment_turn(session_id: str) -> int:
    data = get_session(session_id)
    if not data:
        return 0

    data["turn"] = int(data.get("turn") or 0) + 1
    _save(session_id, data)

    return data["turn"]


def set_last_intent(session_id: str, intent: str | None) -> None:
    data = get_session(session_id)
    if not data:
        return

    data["last_intent"] = intent
    _save(session_id, data)


def set_last_recommendations(session_id: str, recommendations: dict[str, Any] | None) -> None:
    data = get_session(session_id)
    if not data:
        return

    data["last_recommendations"] = recommendations or {}
    _save(session_id, data)


def get_last_recommendations(session_id: str) -> dict[str, Any]:
    data = get_session(session_id)
    if not data:
        return {}

    recommendations = data.get("last_recommendations")
    return recommendations if isinstance(recommendations, dict) else {}


def add_turn(session_id: str, user: str, bot: str) -> None:
    data = get_session(session_id)
    if not data:
        return

    history = data.setdefault("history", [])
    history.append(
        {
            "user": user,
            "bot": bot,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )

    data["turn"] = int(data.get("turn") or 0) + 1
    _save(session_id, data)


def get_context(session_id: str, last_n: int = 3) -> str:
    data = get_session(session_id)
    if not data:
        return ""

    history = data.get("history", [])[-last_n:]
    messages = []

    for item in history:
        user_text = (item.get("user") or "").strip()
        bot_text = (item.get("bot") or "").strip()

        if user_text:
            messages.append(f"Usuário: {user_text}")
        if bot_text:
            messages.append(f"Totem: {bot_text}")

    return "\n".join(messages)


def get_state(session_id: str) -> str:
    data = get_session(session_id)
    if not data:
        return "idle"

    return data.get("state", "idle")


def set_state(session_id: str, state: str) -> None:
    data = get_session(session_id)
    if not data:
        return

    data["state"] = state
    _save(session_id, data)
