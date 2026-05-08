from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def new_correlation_id() -> str:
    value = uuid.uuid4().hex
    correlation_id_var.set(value)
    return value


def get_correlation_id() -> str:
    value = correlation_id_var.get()
    return value or new_correlation_id()


def log_event(event: str, **payload: Any) -> None:
    Path("runtime/logs").mkdir(parents=True, exist_ok=True)

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": get_correlation_id(),
        "event": event,
        **payload,
    }

    with Path("runtime/logs/structured.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    logging.getLogger("totem").info(json.dumps(row, ensure_ascii=False, default=str))
