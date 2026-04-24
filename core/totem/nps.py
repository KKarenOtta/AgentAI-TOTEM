import json
import os
from datetime import datetime
from typing import Optional

from core.totem.metrics import MetricsLogger


metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")


def save_nps(company_id: str, session_id: str, score: int, comment: Optional[str]) -> None:
    os.makedirs("data/nps", exist_ok=True)
    path = "data/nps/nps.jsonl"

    event = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": company_id,
        "session_id": session_id,
        "score": score,
        "comment": comment,
    }

    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=False) + "\n")

    metrics_event = {
        "event": "nps",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": company_id,
        "session_id": session_id,
        "nps_score": score,
        "nps_comment": comment,
    }

    try:
        metrics_logger.save(metrics_event)
        metrics_logger.build_report()
    except Exception:
        pass
