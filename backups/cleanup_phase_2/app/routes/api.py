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
from core.totem.coupon_store import redeem_coupon
from core.totem.lead_store import save_lead
from core.totem.metrics import MetricsLogger
from core.totem.qr import generate_qr_from_text
from core.totem.recovery_store import save_session_handoff
from core.totem.schemas import (
    TotemTrackRequest,
    TotemTrackResponse,
    TotemLeadCaptureRequest,
    TotemLeadCaptureResponse,
)


router = APIRouter(tags=["api"])

METRICS_CSV = "data/metrics/metrics.csv"
metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")
UPLOAD_DIR = Path("static/uploads/campaigns")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _get_public_base_url() -> str:
    base_url = (
        os.getenv("TOTEM_PUBLIC_BASE_URL")
        or os.getenv("APP_BASE_URL")
        or "http://127.0.0.1:8000"
    ).strip()
    return base_url.rstrip("/")


@router.get("/api/events/{company_id}")
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


@router.get("/api/metrics/{company_id}")
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
        for profile in df["profile"].dropna().tolist():
            age_range = None

            if isinstance(profile, dict):
                age_range = profile.get("age_range")
            else:
                text = str(profile)
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


@router.get("/api/dashboard/{company_id}")
def get_marketing_dashboard(company_id: str):
    data = metrics_logger.build_dashboard(company_id)
    return JSONResponse(data)


@router.get("/api/campaigns/{company_id}")
def api_list_campaigns(company_id: str):
    return JSONResponse({"campaigns": list_campaigns(company_id)})


@router.post("/api/campaigns/{company_id}")
def api_create_campaign(company_id: str, payload: Dict[str, Any]):
    created = create_campaign(company_id, payload)
    return JSONResponse(created)


@router.post("/api/campaigns/{company_id}/upload")
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

        with out_path.open("wb") as file:
            file.write(await image.read())

        payload["media_image"] = f"/static/uploads/campaigns/{filename}"

    created = create_campaign(company_id, payload)
    return JSONResponse(created)


@router.patch("/api/campaigns/{company_id}/{campaign_id}")
def api_update_campaign(company_id: str, campaign_id: str, payload: Dict[str, Any]):
    updated = update_campaign(company_id, campaign_id, payload)
    return JSONResponse(updated)


@router.delete("/api/campaigns/{company_id}/{campaign_id}")
def api_delete_campaign(company_id: str, campaign_id: str):
    delete_campaign(company_id, campaign_id)
    return JSONResponse({"ok": True})


@router.post("/api/track", response_model=TotemTrackResponse)
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
    except Exception as exc:
        return TotemTrackResponse(ok=False, message=f"track_error: {type(exc).__name__}: {exc}")


@router.post("/api/lead-capture", response_model=TotemLeadCaptureResponse)
def api_lead_capture(req: TotemLeadCaptureRequest) -> TotemLeadCaptureResponse:
    if not req.lgpd_consent:
        return TotemLeadCaptureResponse(
            ok=False,
            message="É obrigatório aceitar os termos LGPD.",
            lead_id=None,
            access_qr_url=None,
            recovery_qr_url=None,
        )

    try:
        lead = save_lead(req.model_dump())

        return TotemLeadCaptureResponse(
            ok=True,
            message="Cadastro registrado com sucesso.",
            lead_id=lead["lead_id"],
            access_qr_url=lead.get("access_qr_url"),
            recovery_qr_url=lead.get("recovery_qr_url"),
        )
    except Exception as exc:
        return TotemLeadCaptureResponse(
            ok=False,
            message=f"lead_capture_error: {type(exc).__name__}: {exc}",
            lead_id=None,
            access_qr_url=None,
            recovery_qr_url=None,
        )


@router.post("/api/mobile-handoff")
def api_mobile_handoff(payload: Dict[str, Any]):
    company_id = (payload.get("company_id") or "").strip()
    session_id = (payload.get("session_id") or "").strip()

    if not company_id or not session_id:
        return JSONResponse(
            {"ok": False, "message": "company_id e session_id são obrigatórios"},
            status_code=400,
        )

    handoff = save_session_handoff(
        {
            "company_id": company_id,
            "session_id": session_id,
            "research_summary": payload.get("research_summary") or "",
            "recommendations_snapshot": payload.get("recommendations_snapshot") or {},
            "source": payload.get("source") or "totem_live",
        }
    )

    mobile_url = f"{_get_public_base_url()}/mobile/start/{session_id}"
    qr_url = generate_qr_from_text(mobile_url)

    return JSONResponse(
        {
            "ok": True,
            "handoff_id": handoff["handoff_id"],
            "mobile_url": mobile_url,
            "qr_url": qr_url,
        }
    )


@router.post("/api/coupons/redeem")
def api_redeem_coupon(payload: Dict[str, Any]):
    coupon_id = (payload.get("coupon_id") or "").strip()
    store_id = (payload.get("store_id") or "").strip() or None
    operator_id = (payload.get("operator_id") or "").strip() or None

    if not coupon_id:
        return JSONResponse(
            {"ok": False, "message": "coupon_id obrigatório"},
            status_code=400,
        )

    coupon = redeem_coupon(
        coupon_id=coupon_id,
        store_id=store_id,
        operator_id=operator_id,
    )

    if not coupon:
        return JSONResponse(
            {"ok": False, "message": "Cupom não encontrado"},
            status_code=404,
        )

    return JSONResponse(
        {
            "ok": True,
            "message": coupon.get("validation_message") or "Cupom processado.",
            "coupon": coupon,
        }
    )
