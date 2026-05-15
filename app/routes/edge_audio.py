from fastapi import APIRouter
from pydantic import BaseModel

from app.services.edge_audio_capture import record_question
from app.services.cloud_api_client import cloud_interact
from app.services.edge_push import publish

router = APIRouter()

class EdgeInteractRequest(BaseModel):
    company_id: str
    session_id: str

@router.post("/edge/interact/audio")
async def edge_interact_audio(payload: EdgeInteractRequest):
    audio_path = record_question(payload.session_id)

    result = cloud_interact(
        company_id=payload.company_id,
        session_id=payload.session_id,
        message="",
        audio_path=audio_path,
    )

    await publish(payload.session_id, result)
    return {"status": "ok"}
