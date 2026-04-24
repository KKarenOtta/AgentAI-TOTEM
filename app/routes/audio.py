from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.totem.stt import stt_from_base64

router = APIRouter(tags=["audio"])


class AudioRequest(BaseModel):
    audio_base64: str


@router.post("/api/audio/transcribe")
def transcribe(req: AudioRequest):
    if not req.audio_base64:
        raise HTTPException(status_code=400, detail="audio_base64 requerido")

    text, latency, provider = stt_from_base64(req.audio_base64)

    return {
        "text": text,
        "latency": latency,
        "provider": provider
    }
