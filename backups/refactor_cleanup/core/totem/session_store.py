from __future__ import annotations

import json
import os
from datetime import datetime

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def _key(session_id):
    return f"totem:session:{session_id}"


def get_or_create_session(company_id, session_id, profile=None):
    key = _key(session_id)

    if not r.exists(key):
        r.set(key, json.dumps({
            "session_id": session_id,
            "company_id": company_id,
            "created_at": datetime.now().isoformat(),
            "history": [],
            "last_intent": None
        }))

    return get_session(session_id)


def get_session(session_id):
    data = r.get(_key(session_id))
    return json.loads(data) if data else None


def set_last_intent(session_id, intent):
    st = get_session(session_id)
    if not st:
        return
    st["last_intent"] = intent
    r.set(_key(session_id), json.dumps(st))


def add_turn(session_id, user, bot):
    st = get_session(session_id)
    if not st:
        return

    st["history"].append({
        "user": user,
        "bot": bot,
        "ts": datetime.now().isoformat()
    })

    r.set(_key(session_id), json.dumps(st))


def get_context(session_id, last_n=3):
    st = get_session(session_id)
    if not st:
        return ""

    history = st.get("history", [])[-last_n:]
    return " ".join([h["user"] for h in history if h["user"]])
