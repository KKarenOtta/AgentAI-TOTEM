from __future__ import annotations

import logging
import os
import threading

import requests
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


def get_voice_server_url() -> str:
    return os.getenv(
        "VOICE_SERVER_URL",
        "http://127.0.0.1:5000",
    ).rstrip("/")


def get_runtime_mode() -> str:
    return os.getenv(
        "VOICE_RUNTIME_MODE",
        "legacy",
    ).strip().lower()


def run_internal_capture(session_id: str) -> None:
    from edge.voice_agent import capture_once

    capture_once(session_id)


def run_legacy_capture(session_id: str) -> dict:
    voice_server_url = get_voice_server_url()

    response = requests.post(
        f"{voice_server_url}/capture",
        json={"session_id": session_id},
        timeout=90,
    )

    return {
        "ok": response.status_code < 400,
        "status_code": response.status_code,
        "voice_server_url": voice_server_url,
        "response": response.text[:500],
    }


@router.post("/capture")
def capture(session_id: str):
    session_id = (session_id or "").strip()

    if not session_id:
        return {
            "ok": False,
            "error": "session_id obrigatório",
        }

    runtime_mode = get_runtime_mode()

    if runtime_mode == "internal":
        try:
            thread = threading.Thread(
                target=run_internal_capture,
                args=(session_id,),
                daemon=True,
            )

            thread.start()

            return {
                "ok": True,
                "mode": "internal",
                "session_id": session_id,
            }

        except Exception as exc:
            logger.exception(
                "Erro no runtime interno de voz | session_id=%s",
                session_id,
            )

            return {
                "ok": False,
                "mode": "internal",
                "error": str(exc),
            }

    try:
        result = run_legacy_capture(session_id)

        if not result["ok"]:
            return {
                "ok": False,
                "mode": "legacy",
                "session_id": session_id,
                "voice_server_url": result.get("voice_server_url"),
                "status_code": result.get("status_code"),
                "error": result.get("response"),
            }

        return {
            "ok": True,
            "mode": "legacy",
            "session_id": session_id,
            "voice_server_url": result.get("voice_server_url"),
        }

    except Exception as exc:
        logger.exception(
            "Erro no runtime legado de voz | session_id=%s",
            session_id,
        )

        return {
            "ok": False,
            "mode": "legacy",
            "session_id": session_id,
            "voice_server_url": get_voice_server_url(),
            "error": str(exc),
        }
