from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, Query

from core.totem.orchestrator import TotemOrchestrator
from core.totem.stt import stt_from_base64
from infra.realtime.event_bus import publish

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])
orchestrator = TotemOrchestrator()


def get_voice_server_url() -> str:
    return os.getenv("VOICE_SERVER_URL", "http://127.0.0.1:5000").rstrip("/")


def get_default_company_id() -> str:
    return os.getenv("COMPANY_ID", "FLX-001").strip() or "FLX-001"


def audio_file_to_base64(audio_path: str | None) -> str | None:
    if not audio_path:
        return None

    path = Path(audio_path)
    if not path.exists():
        return None

    return base64.b64encode(path.read_bytes()).decode("utf-8")


def publish_voice_status(
    company_id: str,
    session_id: str,
    status: str,
    text: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    publish(
        company_id=company_id,
        event="voice_status",
        payload={
            "company_id": company_id,
            "session_id": session_id,
            "status": status,
            "text": text,
            "payload": payload or {},
        },
    )


def request_raspberry_audio(session_id: str) -> dict[str, Any]:
    voice_server_url = get_voice_server_url()

    response = requests.post(
        f"{voice_server_url}/capture-audio",
        json={"session_id": session_id},
        timeout=120,
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "ok": False,
            "error": response.text[:500],
        }

    data["voice_server_url"] = voice_server_url
    data["status_code"] = response.status_code

    if response.status_code >= 400:
        data["ok"] = False

    return data


def should_ignore_text(text: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < int(os.getenv("VOICE_MIN_TEXT_CHARS", "3")):
        return True

    lower = cleaned.lower()
    ignored_fragments = (
        "legendas",
        "subtitles",
        "obrigado por assistir",
        "thanks for watching",
    )

    return any(fragment in lower for fragment in ignored_fragments)


@router.post("/capture")
def capture(
    session_id: str = Query(..., min_length=1),
    company_id: str | None = Query(default=None),
) -> dict[str, Any]:
    sid = session_id.strip()
    cid = (company_id or get_default_company_id()).strip()

    publish_voice_status(
        company_id=cid,
        session_id=sid,
        status="listening",
        text="Estou ouvindo sua pergunta.",
    )

    try:
        capture_payload = request_raspberry_audio(sid)
    except Exception as exc:
        logger.exception("Erro ao capturar áudio no Raspberry | session_id=%s", sid)

        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="capture_error",
            text="Não consegui acionar o microfone do Raspberry.",
            payload={
                "voice_server_url": get_voice_server_url(),
                "error": str(exc),
            },
        )

        return {
            "ok": False,
            "session_id": sid,
            "company_id": cid,
            "stage": "capture",
            "voice_server_url": get_voice_server_url(),
            "error": str(exc),
        }

    if not capture_payload.get("ok"):
        error = capture_payload.get("error") or "Falha ao capturar áudio no Raspberry."
        status = "silence" if error == "silence" else "capture_error"

        message = (
            "Não consegui ouvir sua pergunta. Tente novamente."
            if status == "silence"
            else "Não consegui capturar o áudio no Raspberry."
        )

        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status=status,
            text=message,
            payload={
                "rms": capture_payload.get("rms"),
                "min_rms": capture_payload.get("min_rms"),
                "audio_device": capture_payload.get("audio_device"),
                "voice_server_url": capture_payload.get("voice_server_url"),
                "status_code": capture_payload.get("status_code"),
                "error": error,
            },
        )

        return {
            "ok": False,
            "session_id": sid,
            "company_id": cid,
            "stage": "capture",
            "error": error,
            "capture": {
                "rms": capture_payload.get("rms"),
                "min_rms": capture_payload.get("min_rms"),
                "audio_device": capture_payload.get("audio_device"),
                "voice_server_url": capture_payload.get("voice_server_url"),
                "status_code": capture_payload.get("status_code"),
            },
        }

    audio_base64 = capture_payload.get("audio_base64") or ""
    if not audio_base64:
        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="capture_error",
            text="O Raspberry não retornou áudio.",
            payload={
                "voice_server_url": capture_payload.get("voice_server_url"),
            },
        )

        return {
            "ok": False,
            "session_id": sid,
            "company_id": cid,
            "stage": "capture",
            "error": "audio_base64 ausente",
        }

    try:
        text, latency, provider = stt_from_base64(audio_base64)
        text = (text or "").strip()

        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="transcribed",
            text=text,
            payload={
                "provider": provider,
                "latency": latency,
                "rms": capture_payload.get("rms"),
            },
        )
    except Exception as exc:
        logger.exception("Erro STT | session_id=%s", sid)

        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="empty_transcription",
            text="Não consegui transcrever sua pergunta.",
            payload={"error": str(exc)},
        )

        return {
            "ok": False,
            "session_id": sid,
            "company_id": cid,
            "stage": "stt",
            "error": str(exc),
        }

    if not text or should_ignore_text(text):
        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="empty_transcription",
            text="Não consegui entender sua pergunta. Tente novamente.",
        )

        return {
            "ok": False,
            "session_id": sid,
            "company_id": cid,
            "stage": "stt",
            "error": "empty_transcription",
            "transcription": text,
        }

    try:
        resposta, recommendations, audio_path, metric, idioma = orchestrator.interact(
            company_id=cid,
            session_id=sid,
            pergunta=text,
            profile={
                "source": "raspberry_voice",
                "input_mode": "voice",
                "device_id": capture_payload.get("device_id"),
                "audio_device": capture_payload.get("audio_device"),
                "rms": capture_payload.get("rms"),
            },
            prefer_audio=True,
        )

        answer_audio_base64 = audio_file_to_base64(audio_path)

        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="answer_ready",
            text=resposta,
            payload={
                "audio_base64": answer_audio_base64,
                "audio_path": audio_path,
                "audio_base64_len": len(answer_audio_base64 or ""),
                "metric": metric,
                "language": idioma,
                "transcription": text,
                "recommendations": recommendations,
            },
        )

        return {
            "ok": True,
            "session_id": sid,
            "company_id": cid,
            "transcription": text,
            "text": resposta,
            "audio_path": audio_path,
            "audio_base64_len": len(answer_audio_base64 or ""),
            "metric": metric,
            "language": idioma,
        }

    except Exception as exc:
        logger.exception("Erro ao gerar resposta/TTS | session_id=%s", sid)

        publish_voice_status(
            company_id=cid,
            session_id=sid,
            status="interaction_error",
            text="Não consegui processar sua pergunta agora.",
            payload={"error": str(exc)},
        )

        return {
            "ok": False,
            "session_id": sid,
            "company_id": cid,
            "stage": "interaction",
            "error": str(exc),
        }
