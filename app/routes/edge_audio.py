from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.aws_db_service import AWSDBService
from app.services.edge_audio_capture import record_question
from app.services.edge_push import publish
from app.services.interaction_service import process_interaction

router = APIRouter()
db = AWSDBService()


class EdgeAudioInteractRequest(BaseModel):
    company_id: str
    session_id: str


@router.post("/edge/interact/audio")
async def edge_interact_audio(payload: EdgeAudioInteractRequest):
    audio_path = None

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

        await db.save_interaction(
            session_id=payload.session_id,
            company_id=payload.company_id,
            message_user=result.get("question_text", ""),
            message_bot=result.get("answer_text", ""),
            input_mode=result.get("input_mode", "audio"),
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

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass
