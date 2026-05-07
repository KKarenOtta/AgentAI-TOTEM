from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.persistence.jsonl_store import append_jsonl, read_jsonl, write_jsonl


SYNC_QUEUE_PATH = Path("data/sync/pending_sync.jsonl")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def enqueue_sync(
    entity: str,
    operation: str,
    payload: dict[str, Any],
    company_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    item = {
        "sync_id": uuid4().hex,
        "timestamp": _now(),
        "entity": entity,
        "operation": operation,
        "company_id": company_id or payload.get("company_id"),
        "session_id": session_id or payload.get("session_id"),
        "payload": payload,
        "status": "pending",
        "attempts": 0,
        "last_error": None,
        "synced_at": None,
    }

    append_jsonl(SYNC_QUEUE_PATH, item)

    return item


def list_pending(limit: int = 100) -> list[dict[str, Any]]:
    rows = read_jsonl(SYNC_QUEUE_PATH)

    pending = [
        row
        for row in rows
        if row.get("status") in {"pending", "failed"}
    ]

    return pending[:limit]


def mark_synced(sync_id: str) -> None:
    rows = read_jsonl(SYNC_QUEUE_PATH)

    for row in rows:
        if row.get("sync_id") == sync_id:
            row["status"] = "synced"
            row["synced_at"] = _now()
            row["last_error"] = None
            break

    write_jsonl(SYNC_QUEUE_PATH, rows)


def mark_failed(sync_id: str, error: str) -> None:
    rows = read_jsonl(SYNC_QUEUE_PATH)

    for row in rows:
        if row.get("sync_id") == sync_id:
            row["status"] = "failed"
            row["attempts"] = int(row.get("attempts") or 0) + 1
            row["last_error"] = str(error)[:500]
            break

    write_jsonl(SYNC_QUEUE_PATH, rows)


def build_sync_status() -> dict[str, int]:
    rows = read_jsonl(SYNC_QUEUE_PATH)

    status = {
        "pending": 0,
        "failed": 0,
        "synced": 0,
        "total": len(rows),
    }

    for row in rows:
        value = row.get("status")

        if value in status:
            status[value] += 1

    return status
