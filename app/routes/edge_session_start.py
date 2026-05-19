from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EdgeSessionStartRequest(BaseModel):
    company_id: str
    session_id: str


@router.post("/edge/session/start")
async def edge_session_start(payload: EdgeSessionStartRequest):
    return {
        "ok": True,
        "session_id": payload.session_id,
        "message": "Sessao iniciada no edge.",
    }
