from __future__ import annotations

import queue
import threading
from collections import defaultdict
from typing import Any

_SUBSCRIBERS: dict[str, list[queue.Queue[dict[str, Any]]]] = defaultdict(list)
_LOCK = threading.Lock()


def subscribe(company_id: str) -> queue.Queue[dict[str, Any]]:
    subscriber: queue.Queue[dict[str, Any]] = queue.Queue()

    with _LOCK:
        _SUBSCRIBERS[company_id].append(subscriber)

    return subscriber


def unsubscribe(company_id: str, subscriber: queue.Queue[dict[str, Any]]) -> None:
    with _LOCK:
        subscribers = _SUBSCRIBERS.get(company_id, [])

        if subscriber in subscribers:
            subscribers.remove(subscriber)

        if not subscribers and company_id in _SUBSCRIBERS:
            del _SUBSCRIBERS[company_id]


def publish(company_id: str, event: str, payload: dict[str, Any]) -> None:
    data = {
        "type": event,
        "payload": payload,
    }

    with _LOCK:
        subscribers = list(_SUBSCRIBERS.get(company_id, []))

    for subscriber in subscribers:
        subscriber.put(data)


def get_queue(company_id: str) -> queue.Queue[dict[str, Any]]:
    return subscribe(company_id)
