from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.edge_audio_capture import record_question
from app.services.edge_push import publish
from app.services.interaction_service import process_interaction

router = APIRouter()


class EdgeAudioInteractRequest(BaseModel):
    company_id: str
    session_id: str


@router.post("/edge/interact/audio")
async def edge_interact_audio(payload: EdgeAudioInteractRequest):
    try:
        audio_path = record_question(payload.session_id)

        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        result = process_interaction(
            company_id=payload.company_id,
            session_id=payload.session_id,
            message="",
            audio_bytes=audio_bytes,
        )

        await publish(payload.session_id, result)

        return {
            "status": "ok",
            "session_id": payload.session_id,
            "audio_path": audio_path,
            "cloud_result": result,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
