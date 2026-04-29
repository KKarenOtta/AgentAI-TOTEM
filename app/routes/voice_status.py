from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from infra.realtime.event_bus import publish

router = APIRouter(prefix="/api/voice", tags=["voice"])


class VoiceStatusRequest(BaseModel):
    company_id: str = Field(..., min_length=1)
    session_id: str | None = None
    status: str = Field(..., min_length=1)
    text: str | None = None
    payload: dict[str, Any] | None = None


@router.post("/status")
def voice_status(req: VoiceStatusRequest) -> dict[str, bool]:
    publish(
        company_id=req.company_id,
        event="voice_status",
        payload={
            "session_id": req.session_id,
            "status": req.status,
            "text": req.text,
            "payload": req.payload or {},
        },
    )
    return {"ok": True}
