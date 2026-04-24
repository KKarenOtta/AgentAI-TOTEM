from __future__ import annotations

import base64
import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException

from core.totem.metrics import MetricsLogger
from core.totem.nps import save_nps
from core.totem.orchestrator import TotemOrchestrator
from core.totem.schemas import (
    TotemActivateRequest,
    TotemActivateResponse,
    TotemInteractRequest,
    TotemInteractResponse,
    TotemNPSRequest,
    TotemNPSResponse,
)
from core.totem.session_store import get_or_create_session, increment_turn
from core.totem.stt import stt_from_base64
from core.totem.tts import gerar_audio

metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")
logger = logging.getLogger("totem")

router = APIRouter(prefix="/totem", tags=["totem"])
orchestrator = TotemOrchestrator()


def audio_file_to_base64(audio_path: str | None) -> str | None:
    audio_path = (audio_path or "").strip()

    if not audio_path or not os.path.exists(audio_path):
        return None

    try:
        with open(audio_path, "rb") as file:
            return base64.b64encode(file.read()).decode("utf-8")
    except Exception as exc:
        logger.warning("Falha ao converter áudio para base64: %s", exc)
        return None


@router.post("/activate", response_model=TotemActivateResponse)
def totem_activate(req: TotemActivateRequest) -> TotemActivateResponse:
    profile_dict = (
        req.profile.model_dump()
        if hasattr(req.profile, "model_dump")
        else (req.profile or None)
    )

    st = get_or_create_session(req.company_id, req.session_id, profile_dict)

    greeting = "Olá! Como posso te ajudar hoje?"
    audio_base64 = None
    audio_provider = None
    audio_error = None
    audio_latency_s = None
    audio_status_code = None

    if req.prefer_audio:
        audio_path, audio_provider, audio_status_code, audio_error, audio_latency_s = gerar_audio(greeting, "pt")
        audio_base64 = audio_file_to_base64(audio_path)

    metrics_logger.save(
        {
            "event": "totem_activate",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "company_id": req.company_id,
            "session_id": st["session_id"] if isinstance(st, dict) else st.session_id,
            "tts_provider": audio_provider,
            "tts_status_code": audio_status_code,
            "tts_error": audio_error,
            "tts_latency_s": audio_latency_s,
            "audio_generated": bool(audio_base64),
        }
    )

    return TotemActivateResponse(
        session_id=st["session_id"] if isinstance(st, dict) else st.session_id,
        language="pt",
        greeting=greeting,
        next="listening",
        audio_base64=audio_base64,
        audio_provider=audio_provider,
        audio_error=audio_error,
    )


@router.post("/interact", response_model=TotemInteractResponse)
def totem_interact(req: TotemInteractRequest) -> TotemInteractResponse:
    profile_dict = req.profile.model_dump() if req.profile else None

    get_or_create_session(req.company_id, req.session_id, profile_dict)
    turn = increment_turn(req.session_id)

    pergunta = (req.message or "").strip()
    stt_latency = None
    stt_provider = None

    if req.audio_base64:
        pergunta, stt_latency, stt_provider = stt_from_base64(req.audio_base64)
        pergunta = (pergunta or "").strip()

    text, recs, audio_path, metric, idioma = orchestrator.interact(
        company_id=req.company_id,
        session_id=req.session_id,
        pergunta=pergunta,
        profile=profile_dict,
        prefer_audio=req.prefer_audio,
        turn=turn,
        input_mode=("audio" if req.audio_base64 else (req.input_mode or "text")),
        stt_provider=stt_provider,
        stt_latency_s=stt_latency,
        message_id=req.message_id,
    )

    audio_base64 = audio_file_to_base64(audio_path)

    return TotemInteractResponse(
        session_id=req.session_id,
        language=idioma,
        text=text,
        recommendations=recs,
        audio_base64=audio_base64,
        audio_provider=metric.get("tts_provider"),
        response_source=metric.get("response_source") or metric.get("source"),
        metrics=metric,
    )


@router.post("/nps", response_model=TotemNPSResponse)
def totem_nps(req: TotemNPSRequest) -> TotemNPSResponse:
    if req.score < 0 or req.score > 10:
        raise HTTPException(status_code=400, detail="score deve estar entre 0 e 10")

    save_nps(req.company_id, req.session_id, req.score, req.comment)

    metrics_logger.save(
        {
            "event": "nps_submitted",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "company_id": req.company_id,
            "session_id": req.session_id,
            "nps_score": req.score,
            "nps_comment": req.comment,
        }
    )

    return TotemNPSResponse(ok=True, message="Obrigado pela avaliação!")
