from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from services.transcription_service import transcribe_audio

router = APIRouter(tags=["audio"])

ALLOWED_SUFFIXES = {".wav", ".mp3", ".m4a", ".ogg", ".webm"}
TEMP_DIR = Path("/tmp/agentai_audio")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/api/audio/transcribe")
async def transcribe_audio_route(file: UploadFile = File(...)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()

    if suffix and suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Formato de áudio não suportado: {suffix}",
        )

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix or ".wav",
        dir=TEMP_DIR,
    )
    temp_path = Path(temp_file.name)

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not temp_path.exists() or temp_path.stat().st_size == 0:
            raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")

        print(f"[AUDIO] recebido: {temp_path}")

        result = transcribe_audio(temp_path)

        return {
            "text": result["text"],
            "filename": file.filename,
            "content_type": file.content_type,
            "provider": result.get("provider"),
            "model": result.get("model"),
            "fallback_used": result.get("fallback_used", False),
            "openai_error": result.get("openai_error"),
        }

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[AUDIO] erro na transcrição: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao transcrever áudio: {exc}",
        ) from exc
    finally:
        try:
            file.file.close()
        except Exception:
            pass

        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass
