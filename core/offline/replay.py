from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

QUEUE_PATH = Path("data/sync/pending_sync.jsonl")
DEAD_PATH = Path("data/sync/dead_letter.jsonl")
LOCK_PATH = Path("data/sync/pending_sync.lock")


@contextmanager
def queue_lock(timeout: int = 10):
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()

    while LOCK_PATH.exists():
        if time.time() - started > timeout:
            raise TimeoutError("sync queue lock timeout")
        time.sleep(0.2)

    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")

    try:
        yield
    finally:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def read_queue(path: Path = QUEUE_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return rows


def write_queue(rows: list[dict[str, Any]], path: Path = QUEUE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def move_to_dead_letter(item: dict[str, Any], error: str) -> None:
    DEAD_PATH.parent.mkdir(parents=True, exist_ok=True)

    row = {
        **item,
        "dead_letter_error": error,
        "dead_letter_at": time.time(),
    }

    with DEAD_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def deduplicate_queue() -> dict[str, int]:
    with queue_lock():
        rows = read_queue()
        seen = set()
        out = []

        for row in rows:
            key = row.get("sync_id") or json.dumps(row, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue

            seen.add(key)
            out.append(row)

        write_queue(out)

    return {"before": len(rows), "after": len(out), "removed": len(rows) - len(out)}
