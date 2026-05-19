from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config.runtime import CLOUD_BASE_URL
from app.services.edge_audio_capture import record_question
from app.services.edge_push import publish

router = APIRouter()


class EdgeAudioInteractRequest(BaseModel):
    company_id: str
    session_id: str


@router.post("/edge/interact/audio")
async def edge_interact_audio(payload: EdgeAudioInteractRequest):
    if not CLOUD_BASE_URL:
        raise HTTPException(status_code=500, detail="CLOUD_BASE_URL nao configurado.")

    try:
        audio_path = record_question(payload.session_id)

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
            
        print("=== EDGE: audio capturado ===", {
            "session_id": payload.session_id,
            "audio_path": audio_path,
            "audio_size": len(audio_bytes),
        }, flush=True)

        files = {
            "audio_file": (f"{payload.session_id}.wav", audio_bytes, "audio/wav"),
        }

        data = {
            "company_id": payload.company_id,
            "session_id": payload.session_id,
            "message": "",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{CLOUD_BASE_URL}/cloud/interact",
                data=data,
                files=files,
            )

        response.raise_for_status()
        result = response.json()

        print({
            "session_id": payload.session_id,
            "audio_path": audio_path,
            "transcript": result.get("transcript"),
            "question_text": result.get("question_text"),
            "llm_source": result.get("llm_source"),
            "answer_text": result.get("answer_text"),
        }, flush=True)

        await publish(payload.session_id, result)

        return {
            "status": "ok",
            "session_id": payload.session_id,
            "audio_path": audio_path,
            "cloud_result": result,
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Cloud retornou erro: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao conectar na cloud: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
