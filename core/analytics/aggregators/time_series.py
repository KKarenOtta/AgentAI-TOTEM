from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from core.dashboard.service import build_company_dashboard
from core.persistence.jsonl_store import read_jsonl, write_jsonl


METRICS_PATH = Path("data/metrics/metrics.jsonl")
HOURLY_DIR = Path("data/analytics/hourly")
DAILY_DIR = Path("data/analytics/daily")


def _event(row: dict[str, Any]) -> str:
    return str(row.get("event") or row.get("event_type") or "")


def _parse_dt(row: dict[str, Any]) -> datetime | None:
    value = row.get("timestamp") or row.get("created_at")

    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _period(dt: datetime | None, kind: str) -> str:
    if dt is None:
        return "unknown"

    if kind == "hourly":
        return dt.strftime("%Y-%m-%d %H:00")

    return dt.strftime("%Y-%m-%d")


def _rate(part: int | float, total: int | float) -> float:
    return round((float(part) / float(total)) * 100, 2) if total else 0.0


def _mean(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _company_metrics(company_id: str) -> list[dict[str, Any]]:
    rows = read_jsonl(METRICS_PATH)
    return [row for row in rows if row.get("company_id") == company_id]


def _aggregate(company_id: str, kind: str) -> list[dict[str, Any]]:
    buckets = defaultdict(
        lambda: {
            "company_id": company_id,
            "period": "",
            "sessions": set(),
            "interactions": 0,
            "leads": 0,
            "nps_count": 0,
            "nps_values": [],
            "fallback_llm": 0,
            "semantic_hits": 0,
            "latencies": [],
            "sentiment_scores": [],
            "intents": Counter(),
            "sources": Counter(),
        }
    )

    for row in _company_metrics(company_id):
        dt = _parse_dt(row)
        period = _period(dt, kind)
        bucket = buckets[period]
        bucket["period"] = period

        session_id = row.get("session_id")
        if session_id:
            bucket["sessions"].add(session_id)

        event = _event(row)

        if event == "interaction":
            bucket["interactions"] += 1

            source = str(row.get("response_source") or row.get("source") or "unknown")
            bucket["sources"][source] += 1

            if source == "llm":
                bucket["fallback_llm"] += 1

            if source in {"faq", "cache"}:
                bucket["semantic_hits"] += 1

            if row.get("intent"):
                bucket["intents"][str(row.get("intent"))] += 1

            try:
                bucket["latencies"].append(float(row.get("latency") or row.get("latency_total_s")))
            except Exception:
                pass

        elif event == "lead_capture":
            bucket["leads"] += 1

        elif event in {"nps", "nps_submitted"}:
            bucket["nps_count"] += 1
            try:
                bucket["nps_values"].append(int(row.get("nps_score") or row.get("score")))
            except Exception:
                pass

        if row.get("sentiment_score") is not None:
            try:
                bucket["sentiment_scores"].append(float(row.get("sentiment_score")))
            except Exception:
                pass

    output = []

    for period, bucket in sorted(buckets.items()):
        interactions = int(bucket["interactions"])

        output.append(
            {
                "company_id": company_id,
                "period": period,
                "granularity": kind,
                "sessions": len(bucket["sessions"]),
                "interactions": interactions,
                "leads": int(bucket["leads"]),
                "nps_count": int(bucket["nps_count"]),
                "nps_avg": _mean(bucket["nps_values"]),
                "avg_latency": _mean(bucket["latencies"]),
                "avg_sentiment_score": _mean(bucket["sentiment_scores"]),
                "fallback_rate": _rate(bucket["fallback_llm"], interactions),
                "semantic_hit_rate": _rate(bucket["semantic_hits"], interactions),
                "top_intents": [
                    {"name": name, "count": count}
                    for name, count in bucket["intents"].most_common(5)
                ],
                "response_sources": [
                    {"name": name, "count": count}
                    for name, count in bucket["sources"].most_common(5)
                ],
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    return output


def build_time_series(company_id: str) -> dict[str, Any]:
    hourly = _aggregate(company_id, "hourly")
    daily = _aggregate(company_id, "daily")

    HOURLY_DIR.mkdir(parents=True, exist_ok=True)
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    hourly_path = HOURLY_DIR / f"{company_id}.jsonl"
    daily_path = DAILY_DIR / f"{company_id}.jsonl"

    write_jsonl(hourly_path, hourly)
    write_jsonl(daily_path, daily)

    return {
        "company_id": company_id,
        "hourly_path": str(hourly_path),
        "daily_path": str(daily_path),
        "hourly_rows": len(hourly),
        "daily_rows": len(daily),
        "dashboard_snapshot": build_company_dashboard(company_id),
    }
