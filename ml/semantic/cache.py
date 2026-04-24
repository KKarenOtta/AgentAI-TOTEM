from __future__ import annotations

import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def get(key: str):
    return r.get(key)


def set(key: str, value: str, ttl: int = 120):
    r.setex(key, ttl, value)
