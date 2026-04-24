from fastapi import APIRouter
from fastapi.responses import JSONResponse
import json
from pathlib import Path
from collections import Counter

router = APIRouter(prefix="/analytics")

LOG = Path("data/conversation_history.jsonl")

@router.get("/summary")
def summary():
    if not LOG.exists():
        return {}

    data = [json.loads(l) for l in LOG.read_text().splitlines()]

    total = len(data)
    avg_score = sum(d["score"] for d in data) / total if total else 0

    intents = Counter([d.get("intent", "unknown") for d in data])

    return JSONResponse({
        "total": total,
        "avg_score": avg_score,
        "intents": intents
    })
