from __future__ import annotations

import logging
import os
import threading

import requests
from fastapi import APIRouter

from edge.voice_agent import capture_once

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])


def get_voice_server_url() -> str:
    return os.getenv(
        "VOICE_SERVER_URL",
        "http://127.0.0.1:5000",
    ).rstrip("/")


def run_internal_capture(session_id: str) -> None:
    try:
        capture_once(session_id)
    except Exception as exc:
        logger.exception(
            "Erro no runtime interno de voz | session_id=%s | error=%s",
            session_id,
            exc,
        )


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

    runtime_mode = os.getenv(
        "VOICE_RUNTIME_MODE",
        "internal",
    ).strip().lower()

    if runtime_mode == "legacy":
        try:
            result = run_legacy_capture(session_id)

            if not result["ok"]:
                return result

            return {
                "ok": True,
                "mode": "legacy",
                "session_id": session_id,
            }

        except Exception as exc:
            logger.exception(
                "Erro no runtime legado | session_id=%s",
                session_id,
            )

            return {
                "ok": False,
                "mode": "legacy",
                "error": str(exc),
            }

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

    except Exception as internal_exc:
        logger.exception(
            "Falha no runtime interno | fallback legado | session_id=%s",
            session_id,
        )

        try:
            result = run_legacy_capture(session_id)

            if result["ok"]:
                return {
                    "ok": True,
                    "mode": "legacy_fallback",
                    "session_id": session_id,
                }

            return {
                "ok": False,
                "mode": "legacy_fallback",
                "error": result.get("response"),
            }

        except Exception as legacy_exc:
            logger.exception(
                "Falha total runtime voz | session_id=%s",
                session_id,
            )

            return {
                "ok": False,
                "mode": "failed",
                "internal_error": str(internal_exc),
                "legacy_error": str(legacy_exc),
            }
