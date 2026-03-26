from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse

from marketing.campaigns import (
    list_campaigns,
    create_campaign,
    update_campaign,
    delete_campaign,
)
from services.realtime.event_bus import get_queue
from services.totem.metrics import MetricsLogger
from services.totem.schemas import TotemTrackRequest, TotemTrackResponse


router = APIRouter(tags=["api"])

METRICS_CSV = "data/metrics/metrics.csv"
metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")
UPLOAD_DIR = Path("static/uploads/campaigns")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
    empty_payload = {
        "interactions_per_day": [],
        "tts_share": {},
        "age_range": {},
        "avg_latency": {},
    }

    if not os.path.exists(METRICS_CSV):
        return JSONResponse(empty_payload)

    df = pd.read_csv(METRICS_CSV)

    if "company_id" in df.columns:
        df = df[df["company_id"] == company_id]

    if df.empty:
        return JSONResponse(empty_payload)

    if "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date.astype(str)

    interactions_per_day = (
        df.groupby("date").size().reset_index(name="count").tail(days).to_dict(orient="records")
        if "date" in df.columns else []
    )

    tts_share = df["voice_source"].value_counts().to_dict() if "voice_source" in df.columns else {}

    age_counts: Dict[str, int] = {}
    if "profile" in df.columns:
        for p in df["profile"].dropna().tolist():
            age_range = None

            if isinstance(p, dict):
                age_range = p.get("age_range")
            else:
                text = str(p)
                if "age_range" in text:
                    import re
                    match = re.search(r"age_range['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]", text)
                    if match:
                        age_range = match.group(1)

            if age_range:
                age_counts[age_range] = age_counts.get(age_range, 0) + 1

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


@router.get("/campaigns/{company_id}")
def api_list_campaigns(company_id: str):
    return JSONResponse({"campaigns": list_campaigns(company_id)})


@router.post("/campaigns/{company_id}")
def api_create_campaign(company_id: str, payload: Dict[str, Any]):
    created = create_campaign(company_id, payload)
    return JSONResponse(created)


@router.post("/campaigns/{company_id}/upload")
async def api_create_campaign_with_image(
    company_id: str,
    name: str = Form(...),
    description: str = Form(""),
    channel: str = Form("totem"),
    status: str = Form("active"),
    objective: str = Form("conversion"),
    target: str = Form(""),
    cta_label: str = Form("Quero meu desconto"),
    discount_type: str = Form("percent"),
    discount_value: float = Form(0),
    coupon_code: str = Form(""),
    landing_url: str = Form(""),
    priority: str = Form("normal"),
    image: Optional[UploadFile] = File(None),
):
    payload: Dict[str, Any] = {
        "name": name.strip(),
        "description": description.strip(),
        "channel": channel.strip() or "totem",
        "status": status.strip() or "active",
        "objective": objective.strip() or "conversion",
        "cta_label": cta_label.strip() or "Quero meu desconto",
        "discount_type": discount_type.strip() or "percent",
        "discount_value": discount_value,
        "coupon_code": coupon_code.strip(),
        "landing_url": landing_url.strip(),
        "priority": priority.strip() or "normal",
        "target_intents": [item.strip() for item in target.split(",") if item.strip()],
        "qr_mode": "coupon",
    }

    if image and image.filename:
        suffix = Path(image.filename).suffix.lower() or ".jpg"
        filename = f"{company_id}-{uuid4().hex}{suffix}"
        out_path = UPLOAD_DIR / filename

        with out_path.open("wb") as f:
            f.write(await image.read())

        payload["media_image"] = f"/static/uploads/campaigns/{filename}"

    created = create_campaign(company_id, payload)
    return JSONResponse(created)


@router.patch("/campaigns/{company_id}/{campaign_id}")
def api_update_campaign(company_id: str, campaign_id: str, payload: Dict[str, Any]):
    updated = update_campaign(company_id, campaign_id, payload)
    return JSONResponse(updated)


@router.delete("/campaigns/{company_id}/{campaign_id}")
def api_delete_campaign(company_id: str, campaign_id: str):
    delete_campaign(company_id, campaign_id)
    return JSONResponse({"ok": True})


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
        return TotemTrackResponse(ok=True, message="tracked")
    except Exception as e:
        return TotemTrackResponse(ok=False, message=f"track_error: {type(e).__name__}: {e}")
