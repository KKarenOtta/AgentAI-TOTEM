from fastapi import APIRouter
from pydantic import BaseModel

from app.services.edge_push import publish
from app.services.interaction_service import process_interaction

router = APIRouter()


class EdgeInteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str = ""


@router.post("/edge/interact/text")
async def edge_interact_text(payload: EdgeInteractRequest):
    result = process_interaction(
        company_id=payload.company_id,
        session_id=payload.session_id,
        message=payload.message,
        audio_bytes=None,
    )

    await publish(payload.session_id, result)

    return {
        "status": "ok",
        "session_id": payload.session_id,
        "cloud_result": result,
    }
