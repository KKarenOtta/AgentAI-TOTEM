from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import defaultdict
from typing import Any

try:
    import redis
except ImportError:
    redis = None


_SUBSCRIBERS: dict[str, list[queue.Queue[dict[str, Any]]]] = defaultdict(list)
_LOCK = threading.Lock()
_REDIS_THREADS: dict[str, threading.Thread] = {}
_REDIS_STOP: dict[str, threading.Event] = {}


def _redis_url() -> str | None:
    return os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")


def _channel(company_id: str) -> str:
    return f"totem:events:{company_id}"


def _redis_client():
    url = _redis_url()
    if not redis or not url:
        return None

    try:
        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def subscribe(company_id: str) -> queue.Queue[dict[str, Any]]:
    subscriber: queue.Queue[dict[str, Any]] = queue.Queue()

    with _LOCK:
        _SUBSCRIBERS[company_id].append(subscriber)

    _ensure_redis_listener(company_id)
    return subscriber


def unsubscribe(company_id: str, subscriber: queue.Queue[dict[str, Any]]) -> None:
    with _LOCK:
        subscribers = _SUBSCRIBERS.get(company_id, [])

        if subscriber in subscribers:
            subscribers.remove(subscriber)

        if not subscribers and company_id in _SUBSCRIBERS:
            del _SUBSCRIBERS[company_id]
            stop = _REDIS_STOP.get(company_id)
            if stop:
                stop.set()


def publish(company_id: str, event: str, payload: dict[str, Any]) -> None:
    data = {
        "type": event,
        "payload": payload,
    }

    client = _redis_client()
    if client:
        client.publish(_channel(company_id), json.dumps(data, ensure_ascii=False))
        return

    _publish_local(company_id, data)


def get_queue(company_id: str) -> queue.Queue[dict[str, Any]]:
    return subscribe(company_id)


def _publish_local(company_id: str, data: dict[str, Any]) -> None:
    with _LOCK:
        subscribers = list(_SUBSCRIBERS.get(company_id, []))

    for subscriber in subscribers:
        subscriber.put(data)


def _ensure_redis_listener(company_id: str) -> None:
    if not _redis_client():
        return

    with _LOCK:
        thread = _REDIS_THREADS.get(company_id)
        if thread and thread.is_alive():
            return

        stop = threading.Event()
        _REDIS_STOP[company_id] = stop

        thread = threading.Thread(
            target=_redis_listener,
            args=(company_id, stop),
            daemon=True,
            name=f"redis-event-listener-{company_id}",
        )
        _REDIS_THREADS[company_id] = thread
        thread.start()


def _redis_listener(company_id: str, stop: threading.Event) -> None:
    client = _redis_client()
    if not client:
        return

    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(_channel(company_id))

    try:
        while not stop.is_set():
            message = pubsub.get_message(timeout=1.0)

            if not message:
                time.sleep(0.05)
                continue

            raw = message.get("data")
            if not raw:
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            _publish_local(company_id, data)
    finally:
        try:
            pubsub.unsubscribe(_channel(company_id))
            pubsub.close()
        except Exception:
            pass
