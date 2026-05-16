from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.cloud_api_client import cloud_interact
from app.services.edge_push import publish
from app.services.edge_audio_capture import record_question

router = APIRouter()


class EdgeAudioInteractRequest(BaseModel):
    company_id: str
    session_id: str


@router.post("/edge/interact/audio")
async def edge_interact_audio(payload: EdgeAudioInteractRequest):
    try:
        audio_path = record_question(payload.session_id)

        result = cloud_interact(
            company_id=payload.company_id,
            session_id=payload.session_id,
            message="",
            audio_path=audio_path,
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
