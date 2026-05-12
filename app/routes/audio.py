from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core.totem.stt import stt_from_base64

router = APIRouter(tags=["audio"])


class AudioRequest(BaseModel):
    audio_base64: str
    company_id: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/api/audio/transcribe")
async def transcribe(
    file: UploadFile | None = File(default=None),
    audio_base64_form: str | None = Form(default=None, alias="audio_base64"),
    company_id: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    req: AudioRequest | None = None,
):
    """
    Transcreve áudio enviado pelo Totem.

    Formatos aceitos:
    1. multipart/form-data:
       - file=@audio.wav
       - company_id=FLX-001
       - session_id=...

    2. JSON:
       {
         "audio_base64": "...",
         "company_id": "FLX-001",
         "session_id": "..."
       }

    A rota mantém compatibilidade com clientes antigos que enviam base64
    e adiciona suporte ao fluxo real do Raspberry, que envia arquivo WAV.
    """
    audio_base64 = ""

    if file is not None:
        audio_bytes = await file.read()

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="arquivo de áudio vazio")

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    elif audio_base64_form:
        audio_base64 = audio_base64_form

    elif req is not None and req.audio_base64:
        audio_base64 = req.audio_base64
        company_id = company_id or req.company_id
        session_id = session_id or req.session_id

    if not audio_base64:
        raise HTTPException(
            status_code=400,
            detail="envie 'file' via multipart/form-data ou 'audio_base64' via JSON",
        )

    text, latency, provider = stt_from_base64(audio_base64)

    return {
        "ok": True,
        "company_id": company_id,
        "session_id": session_id,
        "text": text,
        "latency": latency,
        "provider": provider,
    }
