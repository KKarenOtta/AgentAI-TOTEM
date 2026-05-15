from fastapi import APIRouter
from pydantic import BaseModel

from app.services.cloud_api_client import cloud_interact
from app.services.edge_push import publish

router = APIRouter()


class EdgeInteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str = ""


@router.post("/edge/interact/text")
async def edge_interact_text(payload: EdgeInteractRequest):
    result = cloud_interact(
        company_id=payload.company_id,
        session_id=payload.session_id,
        message=payload.message,
        audio_path=None,
    )

    await publish(payload.session_id, result)

    return {
        "status": "ok",
        "session_id": payload.session_id,
        "cloud_result": result,
    }
