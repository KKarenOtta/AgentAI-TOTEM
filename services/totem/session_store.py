from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SessionState:
    session_id: str
    company_id: str
    created_at: str
    turn: int = 0
    profile: dict | None = None
    last_intent: str | None = None


_SESSIONS: dict[str, SessionState] = {}


def get_or_create_session(company_id: str, session_id: str, profile: dict | None) -> SessionState:
    if session_id in _SESSIONS:
        st = _SESSIONS[session_id]
        # atualiza profile se vier algo novo
        if profile is not None:
            st.profile = profile
        return st

    st = SessionState(
        session_id=session_id,
        company_id=company_id,
        created_at=datetime.now().isoformat(timespec="seconds"),
        turn=0,
        profile=profile,
    )
    _SESSIONS[session_id] = st
    return st


def increment_turn(session_id: str) -> int:
    st = _SESSIONS.get(session_id)
    if not st:
        return 0
    st.turn += 1
    return st.turn


def set_last_intent(session_id: str, intent: str | None) -> None:
    st = _SESSIONS.get(session_id)
    if st:
        st.last_intent = intent


def get_session(session_id: str) -> SessionState | None:
    return _SESSIONS.get(session_id)