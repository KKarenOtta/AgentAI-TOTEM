from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from core.persistence.jsonl_store import read_jsonl
from core.persistence.sync_queue import build_sync_status
from core.recommendation_feedback.store import build_recommendation_summary
from core.totem.metrics import MetricsLogger


METRICS_PATH = Path("data/metrics/metrics.jsonl")
LEADS_PATH = Path("data/leads/leads.jsonl")
CONSENTS_PATH = Path("data/lgpd/consents.jsonl")
COUPONS_PATH = Path("data/coupons/coupons.jsonl")
NPS_PATH = Path("data/nps/nps.jsonl")
SENTIMENT_PATH = Path("data/sentiment/nps_sentiment.jsonl")


def _rows(path: Path) -> list[dict[str, Any]]:
    try:
        return read_jsonl(path)
    except Exception:
        return []


def _company_rows(rows: list[dict[str, Any]], company_id: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("company_id") == company_id]


def _rate(part: int | float, total: int | float) -> float:
    return round((float(part) / float(total)) * 100, 2) if total else 0.0


def _mean(values: list[float | int]) -> float:
    return round(mean(values), 3) if values else 0.0


def _event(row: dict[str, Any]) -> str:
    return str(row.get("event") or row.get("event_type") or "")


def _parse_date(row: dict[str, Any]) -> str:
    value = row.get("timestamp") or row.get("created_at")

    if not value:
        return "unknown"

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except Exception:
        return str(value)[:10]


def _parse_hour(row: dict[str, Any]) -> str:
    value = row.get("timestamp") or row.get("created_at")

    if not value:
        return "unknown"

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:00")
    except Exception:
        return str(value)[:13]


def _is_redeemed(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "").strip().lower()
    return status == "redeemed" or bool(row.get("redeemed_at"))


def _top_counter(counter: Counter, limit: int = 10) -> list[dict[str, Any]]:
    return [
        {"name": str(name), "count": int(count)}
        for name, count in counter.most_common(limit)
        if name not in {"", "None", "null"}
    ]


def _build_timeseries(metrics: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    daily = defaultdict(lambda: {"sessions": set(), "interactions": 0, "nps": 0, "leads": 0})
    hourly = defaultdict(lambda: {"sessions": set(), "interactions": 0, "nps": 0, "leads": 0})

    for row in metrics:
        day = _parse_date(row)
        hour = _parse_hour(row)
        event = _event(row)
        session_id = row.get("session_id")

        for bucket in (daily[day], hourly[hour]):
            if session_id:
                bucket["sessions"].add(session_id)

            if event == "interaction":
                bucket["interactions"] += 1
            elif event in {"nps", "nps_submitted"}:
                bucket["nps"] += 1
            elif event == "lead_capture":
                bucket["leads"] += 1

    def serialize(data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for key, item in sorted(data.items()):
            rows.append(
                {
                    "period": key,
                    "sessions": len(item["sessions"]),
                    "interactions": item["interactions"],
                    "nps": item["nps"],
                    "leads": item["leads"],
                }
            )
        return rows

    return {
        "daily": serialize(daily),
        "hourly": serialize(hourly),
    }


def _build_campaigns(coupons: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    data = defaultdict(
        lambda: {
            "issued": 0,
            "redeemed": 0,
            "impressions": 0,
            "interactions": 0,
        }
    )

    for coupon in coupons:
        campaign_id = coupon.get("campaign_id") or "unknown"
        data[campaign_id]["issued"] += 1

        if _is_redeemed(coupon):
            data[campaign_id]["redeemed"] += 1

    for row in metrics:
        event = _event(row)

        if event == "campaign_impression":
            for campaign_id in row.get("campaign_ids") or []:
                data[campaign_id]["impressions"] += 1

        campaign_id = row.get("campaign_id")
        if not campaign_id:
            continue

        if event == "interaction":
            data[campaign_id]["interactions"] += 1
        elif event == "coupon_issued":
            data[campaign_id]["issued"] += 1
        elif event == "coupon_redeemed":
            data[campaign_id]["redeemed"] += 1

    campaigns = []
    for campaign_id, item in data.items():
        issued = int(item["issued"])
        redeemed = int(item["redeemed"])
        impressions = int(item["impressions"])

        campaigns.append(
            {
                "campaign_id": campaign_id,
                "impressions": impressions,
                "interactions": int(item["interactions"]),
                "issued": issued,
                "redeemed": redeemed,
                "ctr": _rate(issued, impressions),
                "conversion": _rate(redeemed, issued),
            }
        )

    campaigns.sort(key=lambda row: (row["redeemed"], row["conversion"], row["issued"]), reverse=True)
    return campaigns


def _build_stores(coupons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stores = Counter()

    for coupon in coupons:
        if not _is_redeemed(coupon):
            continue

        store_id = coupon.get("store_id") or coupon.get("redeemed_store_id") or "unknown"
        stores[store_id] += 1

    return [
        {"store_id": str(store_id), "redeemed": int(count)}
        for store_id, count in stores.most_common(10)
    ]


def _build_sentiment(metrics: list[dict[str, Any]], sentiment_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = sentiment_rows[:]

    if not rows:
        rows = [
            row for row in metrics
            if row.get("sentiment") or row.get("sentiment_score") is not None
        ]

    scores = []
    sentiment_counter = Counter()
    risk_counter = Counter()
    nps_class_counter = Counter()

    for row in rows:
        try:
            scores.append(float(row.get("sentiment_score")))
        except Exception:
            pass

        if row.get("sentiment"):
            sentiment_counter[str(row.get("sentiment"))] += 1

        if row.get("frustration_risk"):
            risk_counter[str(row.get("frustration_risk"))] += 1

        if row.get("nps_class"):
            nps_class_counter[str(row.get("nps_class"))] += 1

    return {
        "count": len(rows),
        "avg_sentiment_score": _mean(scores),
        "sentiments": _top_counter(sentiment_counter),
        "frustration_risk": _top_counter(risk_counter),
        "nps_classes": _top_counter(nps_class_counter),
    }


def build_company_dashboard(company_id: str) -> dict[str, Any]:
    metrics = _company_rows(_rows(METRICS_PATH), company_id)
    leads = _company_rows(_rows(LEADS_PATH), company_id)
    consents = _company_rows(_rows(CONSENTS_PATH), company_id)
    coupons = _company_rows(_rows(COUPONS_PATH), company_id)
    nps_rows = _company_rows(_rows(NPS_PATH), company_id)
    sentiment_rows = _company_rows(_rows(SENTIMENT_PATH), company_id)

    legacy = MetricsLogger(path=str(METRICS_PATH)).build_dashboard(company_id)

    session_ids = {
        row.get("session_id")
        for row in metrics
        if row.get("session_id")
    }

    interactions = [
        row for row in metrics
        if _event(row) == "interaction"
    ]

    issued = len(coupons)
    redeemed = sum(1 for row in coupons if _is_redeemed(row))

    nps_values = []
    for row in metrics:
        if _event(row) in {"nps", "nps_submitted"}:
            value = row.get("nps_score") or row.get("score")
            try:
                nps_values.append(int(value))
            except Exception:
                pass

    if not nps_values:
        for row in nps_rows:
            value = row.get("score") or row.get("nps_score")
            try:
                nps_values.append(int(value))
            except Exception:
                pass

    latencies = []
    for row in interactions:
        value = row.get("latency") or row.get("latency_total_s")
        try:
            latencies.append(float(value))
        except Exception:
            pass

    source_counter = Counter(
        str(row.get("response_source") or row.get("source") or "unknown")
        for row in interactions
    )

    intent_counter = Counter(
        str(row.get("intent") or "unknown")
        for row in interactions
        if row.get("intent")
    )

    matched_counter = Counter(
        str(row.get("matched_question") or "")
        for row in interactions
        if row.get("matched_question")
    )

    campaigns = _build_campaigns(coupons=coupons, metrics=metrics)
    stores = _build_stores(coupons)
    sync_health = build_sync_status()

    kpis = {
        "sessions": len(session_ids),
        "interactions": len(interactions),
        "leads": len(leads),
        "consents": len(consents),
        "nps_count": len(nps_values),
        "nps_avg": round(mean(nps_values), 2) if nps_values else 0,
        "issued": issued,
        "redeemed": redeemed,
        "conversion": _rate(redeemed, issued),
        "avg_latency": _mean(latencies),
        "sync_pending": sync_health.get("pending", 0),
        "sync_failed": sync_health.get("failed", 0),
        "sync_synced": sync_health.get("synced", 0),
    }

    return {
        "company_id": company_id,
        "source": "jsonl",
        "kpis": kpis,
        "sync_health": sync_health,
        "timeseries": _build_timeseries(metrics),
        "campaigns": campaigns,
        "stores": stores,
        "sentiment": _build_sentiment(metrics, sentiment_rows),
        "recommendation_feedback": build_recommendation_summary(company_id),
        "ai": {
            "response_sources": _top_counter(source_counter),
            "intents": _top_counter(intent_counter),
            "matched_questions": _top_counter(matched_counter),
            "fallback_rate": _rate(source_counter.get("llm", 0), len(interactions)),
            "semantic_hit_rate": _rate(source_counter.get("faq", 0) + source_counter.get("cache", 0), len(interactions)),
        },
        "legacy": legacy,
    }
