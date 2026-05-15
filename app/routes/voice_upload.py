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

        from array import array

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
    }
