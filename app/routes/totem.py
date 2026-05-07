from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.aws_db_service import AWSDBService
from core.totem.orchestrator import TotemOrchestrator
from core.totem.qr import generate_qr_from_text
from core.totem.recovery_store import save_session_handoff
from core.totem.session_store import (
    get_last_recommendations,
    get_session,
    set_last_recommendations,
)
from core.totem.tts import gerar_audio

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = TotemOrchestrator()
db = AWSDBService()

GREETING_DEFAULT = "Olá! Como posso ajudar você hoje?"
HANDOFF_DIR = Path("data/device_handoffs")


class ActivateRequest(BaseModel):
    company_id: str
    session_id: str
    prefer_audio: Optional[bool] = True


class InteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str
    prefer_audio: Optional[bool] = True
    profile: Optional[dict] = None


class NPSRequest(BaseModel):
    company_id: str
    session_id: str
    score: int
    comment: Optional[str] = None


class EndRequest(BaseModel):
    company_id: str
    session_id: str
    reason: str = "completed"


def _audio_to_base64(path: str | None) -> str | None:
    if not path:
        return None

    audio_path = Path(path)

    if not audio_path.exists():
        return None

    try:
        return base64.b64encode(audio_path.read_bytes()).decode("utf-8")
    except Exception as exc:
        logger.warning("Falha ao converter áudio para base64: %s", exc)
        return None


def _public_base_url() -> str:
    return os.getenv("TOTEM_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _handoff_url(company_id: str, session_id: str) -> str:
    return f"{_public_base_url()}/device/{company_id}/{session_id}"


def _build_summary(session_id: str) -> str:
    session = get_session(session_id) or {}
    history = session.get("history") or []

    if not history:
        return "Sessão iniciada no totem."

    parts = []

    for item in history[-5:]:
        question = (item.get("user") or "").strip()
        answer = (item.get("bot") or "").strip()

        if question:
            parts.append(f"Pergunta: {question}")

        if answer:
            parts.append(f"Resposta: {answer}")

    return "\n".join(parts).strip() or "Sessão iniciada no totem."


def _save_device_handoff(company_id: str, session_id: str, url: str) -> dict:
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)

    summary = _build_summary(session_id)
    recommendations = get_last_recommendations(session_id)

    payload = {
        "company_id": company_id,
        "session_id": session_id,
        "summary": summary,
        "recommendations": recommendations,
        "link": url,
        "map_url": "https://zoologico.com.br/sobre/mapa-zoo-sao-paulo",
    }

    out_path = HANDOFF_DIR / f"{session_id}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    save_session_handoff(
        {
            "company_id": company_id,
            "session_id": session_id,
            "research_summary": summary,
            "recommendations_snapshot": recommendations,
            "source": "totem_device_handoff",
        }
    )

    return payload


@router.post("/totem/activate")
async def totem_activate(payload: ActivateRequest):
    await db.save_session_start(
        session_id=payload.session_id,
        company_id=payload.company_id,
        device_id=None,
    )

    audio_path = None
    audio_base64 = None

    if payload.prefer_audio:
        audio_path, _, _, _, _ = gerar_audio(GREETING_DEFAULT, "pt")
        audio_base64 = _audio_to_base64(audio_path)

    await db.save_event(
        company_id=payload.company_id,
        session_id=payload.session_id,
        event_type="totem_activated",
        payload={"greeting": GREETING_DEFAULT},
    )

    return {
        "status": "activated",
        "session_id": payload.session_id,
        "greeting": GREETING_DEFAULT,
        "audio_path": audio_path,
        "audio_base64": audio_base64,
    }


@router.post("/totem/interact")
async def totem_interact(payload: InteractRequest):
    resposta, recommendations, audio_path, metric, idioma = orchestrator.interact(
        company_id=payload.company_id,
        session_id=payload.session_id,
        pergunta=payload.message,
        profile=payload.profile or {},
        prefer_audio=payload.prefer_audio,
    )

    set_last_recommendations(payload.session_id, recommendations)

    await db.save_interaction(
        session_id=payload.session_id,
        company_id=payload.company_id,
        message_user=payload.message,
        message_bot=resposta,
        response_source=metric.get("response_source"),
        response_time_ms=int(metric.get("latency", 0) * 1000),
        language_detected=idioma,
        llm_meta=metric,
    )

    return {
        "text": resposta,
        "recommendations": {},
        "marketing_locked": True,
        "marketing_message": "Ofertas disponíveis após cadastro e aceite LGPD no device.",
        "audio_path": audio_path,
        "audio_base64": _audio_to_base64(audio_path),
        "metric": metric,
        "language": idioma,
    }


@router.post("/totem/nps")
async def totem_nps(payload: NPSRequest):
    score = max(0, min(10, int(payload.score)))

    await db.save_nps(
        company_id=payload.company_id,
        session_id=payload.session_id,
        score=score,
        comment=payload.comment,
    )

    return {"ok": True, "score": score}


@router.post("/totem/end")
async def totem_end(payload: EndRequest):
    await db.save_session_end(
        session_id=payload.session_id,
        reason=payload.reason,
    )

    url = _handoff_url(payload.company_id, payload.session_id)
    handoff = _save_device_handoff(payload.company_id, payload.session_id, url)
    qr_url = generate_qr_from_text(url)

    await db.save_event(
        company_id=payload.company_id,
        session_id=payload.session_id,
        event_type="totem_session_ended",
        payload={
            "reason": payload.reason,
            "handoff_url": url,
            "handoff_qr_url": qr_url,
            "summary": handoff.get("summary"),
            "recommendations": handoff.get("recommendations"),
        },
    )

    return {
        "ok": True,
        "session_id": payload.session_id,
        "handoff_url": url,
        "handoff_qr_url": qr_url,
        "summary": handoff.get("summary"),
        "recommendations": handoff.get("recommendations"),
        "message": "Atendimento finalizado. Escaneie o QR Code para continuar no celular, fazer o cadastro e acessar as ofertas.",
    }
