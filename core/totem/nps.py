from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.persistence.jsonl_store import append_jsonl
from core.sentiment.engine import analyze_sentiment
from core.totem.metrics import MetricsLogger


NPS_PATH = "data/nps/nps.jsonl"
SENTIMENT_PATH = "data/sentiment/nps_sentiment.jsonl"

metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_nps(company_id: str, session_id: str, score: int, comment: Optional[str]) -> None:
    score = int(score)
    timestamp = _now()

    analysis = analyze_sentiment(
        comment,
        nps_score=score,
        context={
            "company_id": company_id,
            "session_id": session_id,
            "source": "nps",
        },
    )

    event = {
        "timestamp": timestamp,
        "company_id": company_id,
        "session_id": session_id,
        "score": score,
        "comment": comment,
        "analysis": analysis,
    }

    append_jsonl(NPS_PATH, event)

    sentiment_event = {
        "event": "nps_sentiment",
        "timestamp": timestamp,
        "company_id": company_id,
        "session_id": session_id,
        "nps_score": score,
        "nps_comment": comment,
        **analysis,
    }

    append_jsonl(SENTIMENT_PATH, sentiment_event)

    metrics_logger.save(
        {
            "event": "nps",
            "timestamp": timestamp,
            "company_id": company_id,
            "session_id": session_id,
            "nps_score": score,
            "nps_comment": comment,
            "sentiment": analysis.get("sentiment"),
            "sentiment_score": analysis.get("sentiment_score"),
            "nps_class": analysis.get("nps_class"),
            "frustration_risk": analysis.get("frustration_risk"),
            "engagement_score": analysis.get("engagement_score"),
        }
    )
