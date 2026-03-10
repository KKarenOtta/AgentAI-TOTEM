import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from services.totem.metrics import MetricsLogger
from services.totem.schemas import TotemTrackRequest, TotemTrackResponse
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
import pandas as pd
import os

from services.realtime.event_bus import get_queue
from marketing.campaigns import (
    list_campaigns, create_campaign, update_campaign, delete_campaign
)

router = APIRouter(tags=["api"])

METRICS_CSV = "data/metrics/metrics.csv"  # mantenha isso como padrão
metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")

@router.get("/events/{company_id}")
def sse_events(company_id: str):
    def gen():
        q = get_queue(company_id)
        while True:
            try:
                ev = q.get(timeout=10)
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            except Exception:
                yield "data: {\"type\":\"keepalive\"}\n\n"
                time.sleep(0.1)

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/metrics/{company_id}")
def get_metrics(company_id: str, days: int = 7):
    if not os.path.exists(METRICS_CSV):
        return JSONResponse({"interactions_per_day": [], "tts_share": {}, "age_range": {}, "avg_latency": {} })

    df = pd.read_csv(METRICS_CSV)

    # filtra por empresa
    if "company_id" in df.columns:
        df = df[df["company_id"] == company_id]

    if df.empty:
        return JSONResponse({"interactions_per_day": [], "tts_share": {}, "age_range": {}, "avg_latency": {} })

    # timestamp -> date
    if "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date.astype(str)

    # interações por dia
    interactions_per_day = (
        df.groupby("date").size().reset_index(name="count").tail(days).to_dict(orient="records")
        if "date" in df.columns else []
    )

    # share tts
    tts_share = df["voice_source"].value_counts().to_dict() if "voice_source" in df.columns else {}

    # age_range (profile pode estar como string dict — tentamos extrair)
    age_counts: Dict[str, int] = {}
    if "profile" in df.columns:
        for p in df["profile"].dropna().tolist():
            # profile pode vir como dict (quando salvo) ou string
            ar = None
            if isinstance(p, dict):
                ar = p.get("age_range")
            else:
                s = str(p)
                # tentativa simples: procurar "age_range"
                if "age_range" in s:
                    # ex: '... "age_range": "25-34" ...'
                    import re
                    m = re.search(r"age_range['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", s)
                    if m:
                        ar = m.group(1)
            if ar:
                age_counts[ar] = age_counts.get(ar, 0) + 1

    # latências médias
    avg_latency = {}
    if "gen_latency_s" in df.columns:
        avg_latency["gen"] = float(df["gen_latency_s"].dropna().mean())
    if "tts_latency_s" in df.columns:
        avg_latency["tts"] = float(df["tts_latency_s"].dropna().mean())

    return JSONResponse({
        "interactions_per_day": interactions_per_day,
        "tts_share": tts_share,
        "age_range": age_counts,
        "avg_latency": avg_latency,
    })


# ---------------- Campaigns CRUD ----------------

@router.get("/campaigns/{company_id}")
def api_list_campaigns(company_id: str):
    return JSONResponse({"campaigns": list_campaigns(company_id)})

@router.post("/campaigns/{company_id}")
def api_create_campaign(company_id: str, payload: Dict[str, Any]):
    created = create_campaign(company_id, payload)
    return JSONResponse(created)

@router.post("/track", response_model=TotemTrackResponse)
def track_event(req: TotemTrackRequest) -> TotemTrackResponse:
    event_row = {
        "event": req.event,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": req.company_id,
        "session_id": req.session_id,
        "action_id": req.action_id,
        "action_label": req.action_label,
        "campaign_id": req.campaign_id,
        "turn_index": req.turn_index,
        "message_id": req.message_id,
        "value": req.value,
        "meta": req.meta,
    }
    try:
        metrics_logger.save(event_row)
        # não precisa rebuild report toda vez; mas se quiser:
        # metrics_logger.build_report()
        return TotemTrackResponse(ok=True, message="tracked")
    except Exception as e:
        return TotemTrackResponse(ok=False, message=f"track_error: {type(e).__name__}: {e}")

@router.patch("/campaigns/{company_id}/{campaign_id}")
def api_update_campaign(company_id: str, campaign_id: str, payload: Dict[str, Any]):
    updated = update_campaign(company_id, campaign_id, payload)
    return JSONResponse(updated)

@router.delete("/campaigns/{company_id}/{campaign_id}")
def api_delete_campaign(company_id: str, campaign_id: str):
    delete_campaign(company_id, campaign_id)
    return JSONResponse({"ok": True})
