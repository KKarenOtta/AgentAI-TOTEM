from fastapi import APIRouter
from pydantic import BaseModel

from app.services.aws_db_service import AWSDBService
from app.services.edge_push import publish
from app.services.interaction_service import process_interaction

router = APIRouter()
db = AWSDBService()


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

    await db.save_interaction(
        session_id=payload.session_id,
        company_id=payload.company_id,
        message_user=result.get("question_text", ""),
        message_bot=result.get("answer_text", ""),
        input_mode=result.get("input_mode", "text"),
        response_source=result.get("llm_source"),
        response_time_ms=0,
        language_detected=result.get("language"),
        llm_meta={
            "stt_source": result.get("stt_source"),
            "stt_latency": result.get("stt_latency"),
            "llm_source": result.get("llm_source"),
            "tts_source": result.get("tts_source"),
            "tts_status": result.get("tts_status"),
            "tts_error": result.get("tts_error"),
            "tts_latency": result.get("tts_latency"),
            "audio_url": result.get("audio_url"),
        },
    )

    await publish(payload.session_id, result)

    return {
        "status": "ok",
        "session_id": payload.session_id,
        "cloud_result": result,
    }
