from __future__ import annotations

import logging

from fastapi import APIRouter

from infra.realtime.event_bus import publish

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/capture")
def capture(session_id: str):
    session_id = (session_id or "").strip()

    if not session_id:
        return {
            "ok": False,
            "error": "session_id obrigatório",
        }

    try:
        publish(
            company_id="FLX-001",
            event="voice_capture_requested",
            payload={
                "session_id": session_id,
            },
        )

        logger.info(
            "Solicitação de captura enviada | session_id=%s",
            session_id,
        )

        return {
            "ok": True,
            "mode": "edge_capture",
            "session_id": session_id,
            "message": "Solicitação enviada ao Raspberry Pi",
        }

    except Exception as exc:
        logger.exception(
            "Erro ao solicitar captura de voz | session_id=%s",
            session_id,
        )

        return {
            "ok": False,
            "error": str(exc),
        }
