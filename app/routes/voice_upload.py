from __future__ import annotations

import base64
import math
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, UploadFile

from core.totem.orchestrator import TotemOrchestrator
from core.totem.stt import stt_from_base64
from infra.realtime.event_bus import publish

router = APIRouter(prefix="/api/voice", tags=["voice"])

COMPANY_ID = "FLX-001"

orchestrator = TotemOrchestrator()

MIN_RMS = 150
MIN_TEXT_CHARS = 3


def publish_voice_status(
    session_id: str,
    status: str,
    text: str | None = None,
    payload: dict[str, Any] | None = None,
):
    publish(
        company_id=COMPANY_ID,
        event="voice_status",
        payload={
            "session_id": session_id,
            "status": status,
            "text": text,
            "payload": payload or {},
        },
    )


def compute_rms(path: str) -> int:
    try:
        with wave.open(path, "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())

        samples = array("h")
        samples.frombytes(frames)

        if not samples:
            return 0

        total = sum(sample * sample for sample in samples)

        return int(math.sqrt(total / len(samples)))

    except Exception:
        return 0


def should_ignore_text(text: str) -> bool:
    cleaned = (text or "").strip()

    if len(cleaned) < MIN_TEXT_CHARS:
        return True

    return False


@router.post("/upload")
async def upload_voice(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
):
    temp_path = None

    try:
        publish_voice_status(
            session_id,
            "recording",
            "Áudio recebido do Raspberry.",
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
        ) as temp_file:
            temp_file.write(await audio.read())
            temp_path = temp_file.name

        rms = compute_rms(temp_path)

        if rms < MIN_RMS:
            publish_voice_status(
                session_id,
                "silence",
                "Áudio muito baixo.",
                {
                    "rms": rms,
                    "min_rms": MIN_RMS,
                },
            )

            return {
                "ok": False,
                "error": "Áudio muito baixo",
            }

        audio_base64 = base64.b64encode(
            Path(temp_path).read_bytes()
        ).decode("utf-8")

        text, latency, provider = stt_from_base64(audio_base64)

        text = (text or "").strip()

        if not text or should_ignore_text(text):
            publish_voice_status(
                session_id,
                "empty_transcription",
                "Não consegui entender o áudio.",
            )

            return {
                "ok": False,
                "error": "Transcrição vazia",
            }

        publish_voice_status(
            session_id,
            "transcribed",
            text,
            {
                "provider": provider,
                "latency": latency,
            },
        )

        resposta, recommendations, audio_path, metric, idioma = (
            orchestrator.interact(
                company_id=COMPANY_ID,
                session_id=session_id,
                pergunta=text,
                profile={
                    "input_mode": "voice_upload",
                },
                prefer_audio=True,
            )
        )

        response_audio_base64 = None

        if audio_path and Path(audio_path).exists():
            response_audio_base64 = base64.b64encode(
                Path(audio_path).read_bytes()
            ).decode("utf-8")

        publish_voice_status(
            session_id,
            "answer_ready",
            resposta,
            {
                "audio_base64": response_audio_base64,
                "recommendations": recommendations,
                "metric": metric,
                "language": idioma,
            },
        )

        return {
            "ok": True,
            "text": text,
            "response": resposta,
            "audio_base64": response_audio_base64,
            "provider": provider,
            "latency": latency,
            "metric": metric,
            "language": idioma,
        }

    except Exception as exc:
        publish_voice_status(
            session_id,
            "interaction_error",
            str(exc),
        )

        return {
            "ok": False,
            "error": str(exc),
        }

    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception:
                pass
