from __future__ import annotations

import os

import requests
from fastapi import APIRouter

router = APIRouter(prefix="/api/voice", tags=["voice"])


def get_voice_server_url() -> str:
    return os.getenv("VOICE_SERVER_URL", "http://127.0.0.1:5000").rstrip("/")


@router.post("/capture")
def capture(session_id: str):
    voice_server_url = get_voice_server_url()

    try:
        response = requests.post(
            f"{voice_server_url}/capture",
            json={"session_id": session_id},
            timeout=90,
        )

        if response.status_code >= 400:
            return {
                "ok": False,
                "status_code": response.status_code,
                "voice_server_url": voice_server_url,
                "error": response.text,
            }

        return {
            "ok": True,
            "voice_server_url": voice_server_url,
        }

    except Exception as exc:
        return {
            "ok": False,
            "voice_server_url": voice_server_url,
            "error": str(exc),
        }
