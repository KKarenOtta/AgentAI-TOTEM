from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from uuid import uuid4


RECOVERY_PATH = "data/recovery/search_memory.jsonl"
LEADS_PATH = "data/leads/leads.jsonl"
SESSION_HANDOFFS_PATH = "data/recovery/session_handoffs.jsonl"


def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8"):
            pass


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    _ensure_parent(path)

    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def save_session_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_parent(SESSION_HANDOFFS_PATH)

    item = {
        "handoff_id": uuid4().hex,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": payload["company_id"],
        "session_id": payload["session_id"],
        "research_summary": payload.get("research_summary") or "",
        "recommendations_snapshot": payload.get("recommendations_snapshot") or {},
        "source": payload.get("source") or "totem_live",
    }

    with open(SESSION_HANDOFFS_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")

    return item


def get_session_handoff(session_id: str) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl(SESSION_HANDOFFS_PATH)):
        if row.get("session_id") == session_id:
            return row
    return None


def save_recovery_memory(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_parent(RECOVERY_PATH)

    item = {
        "memory_id": uuid4().hex,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": payload["company_id"],
        "session_id": payload["session_id"],
        "lead_id": payload["lead_id"],
        "email": payload["email"].strip().lower(),
        "research_summary": payload.get("research_summary") or "",
        "recommendations_snapshot": payload.get("recommendations_snapshot") or {},
        "source": payload.get("source") or "totem_live",
    }

    with open(RECOVERY_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")

    return item


def get_recovery_memory(memory_id: str) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl(RECOVERY_PATH)):
        if row.get("memory_id") == memory_id:
            return row
    return None


def get_lead_by_id(lead_id: str) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl(LEADS_PATH)):
        if row.get("lead_id") == lead_id:
            return row
    return None


def get_latest_memory_for_lead(lead_id: str) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl(RECOVERY_PATH)):
        if row.get("lead_id") == lead_id:
            return row
    return None
