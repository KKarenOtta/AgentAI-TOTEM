import json
import os
from datetime import datetime
from typing import Optional

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
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # também registra NPS no stream de métricas (dataset-ready)
    nps_event = {
        "event": "nps",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": req.company_id,
        "session_id": req.session_id,
        "nps_score": req.score,
        "nps_comment": req.comment,
    }

    try:
        metrics_logger.save(nps_event)
        metrics_logger.build_report()
    except Exception:
        pass