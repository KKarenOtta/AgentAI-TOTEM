from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.aws_db_service import AWSDBService
from core.totem.orchestrator import TotemOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()
orchestrator = TotemOrchestrator()
db = AWSDBService()

GREETING_DEFAULT = "Olá! Como posso ajudar você hoje?"


class ActivateRequest(BaseModel):
    company_id: str
    session_id: str
    prefer_audio: Optional[bool] = False


class InteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str
    prefer_audio: Optional[bool] = False
    profile: Optional[dict] = None


@router.post("/totem/activate")
async def totem_activate(payload: ActivateRequest):
    await db.save_session_start(
        session_id=payload.session_id,
        company_id=payload.company_id,
        device_id=None,
    )

    greeting = GREETING_DEFAULT
    audio_base64 = None

    try:
        resposta, _, audio_path, metric, _ = orchestrator.interact(
            company_id=payload.company_id,
            session_id=payload.session_id,
            pergunta="saudacao_inicial",
            profile={},
            prefer_audio=payload.prefer_audio,
        )
        if resposta:
            greeting = resposta
    except Exception as exc:
        logger.warning("orchestrator.interact no activate falhou: %s", exc)

    return {
        "status": "activated",
        "session_id": payload.session_id,
        "greeting": greeting,
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

    await db.save_interaction(
        session_id=payload.session_id,
        company_id=payload.company_id,
        message_user=payload.message,
        message_bot=resposta,
        response_source=metric.get("response_source"),
        response_time_ms=int(metric.get("latency", 0) * 1000),
    )

    return {
        "text": resposta,
        "recommendations": recommendations,
        "audio_path": audio_path,
        "metric": metric,
        "language": idioma,
    }
