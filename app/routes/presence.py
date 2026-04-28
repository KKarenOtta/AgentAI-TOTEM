from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.presence.service import PresenceService

router = APIRouter(prefix="/api/presence", tags=["presence"])
presence_service = PresenceService()


class PresenceRequest(BaseModel):
    company_id: str = Field(..., min_length=1)
    device_id: str = Field(..., min_length=1)
    present: bool = True
    source: str | None = None
    active_sensor: str | None = None
    distance_cm: float | None = None
    approaching: bool | None = None
    confidence: float | None = None
    temperature: float | None = None
    humidity: float | None = None
    sensor_payload: dict[str, Any] | None = None
    image_base64: str | None = None


@router.post("/trigger")
def trigger_presence(payload: PresenceRequest) -> dict:
    state = presence_service.trigger(
        company_id=payload.company_id,
        device_id=payload.device_id,
        image_base64=payload.image_base64,
        sensor_payload={
            "present": payload.present,
            "source": payload.source,
            "active_sensor": payload.active_sensor,
            "distance_cm": payload.distance_cm,
            "approaching": payload.approaching,
            "confidence": payload.confidence,
            "temperature": payload.temperature,
            "humidity": payload.humidity,
            "sensor_payload": payload.sensor_payload,
        },
    )
    return {"ok": True, "state": state}


@router.post("/heartbeat")
def heartbeat_presence(payload: PresenceRequest) -> dict:
    state = presence_service.heartbeat(
        company_id=payload.company_id,
        device_id=payload.device_id,
    )
    return {"ok": True, "state": state}


@router.post("/clear")
def clear_presence(payload: PresenceRequest) -> dict:
    state = presence_service.clear(
        company_id=payload.company_id,
        device_id=payload.device_id,
    )
    return {"ok": True, "state": state}
