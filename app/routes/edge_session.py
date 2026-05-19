from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config.runtime import CLOUD_BASE_URL

router = APIRouter()


class EdgeSessionEndRequest(BaseModel):
    company_id: str
    session_id: str
    reason: str = "completed"


def build_cloud_url(base_url: str) -> str:
    base = (base_url or "").rstrip("/")
    if base.endswith("/cloud"):
        base = base[:-6]
    return f"{base}/totem/end"


@router.post("/edge/session/end")
async def edge_session_end(payload: EdgeSessionEndRequest):
    if not CLOUD_BASE_URL:
        raise HTTPException(status_code=500, detail="CLOUD_BASE_URL nao configurado.")

    target_url = build_cloud_url(CLOUD_BASE_URL)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                target_url,
                json={
                    "company_id": payload.company_id,
                    "session_id": payload.session_id,
                    "reason": payload.reason,
                },
            )

        response.raise_for_status()
        data = response.json()

        return {
            "ok": data.get("ok", True),
            "session_id": data.get("session_id") or data.get("sessionId") or payload.session_id,
            "message": data.get("message", ""),
            "summary": data.get("summary", ""),
            "recommendations": data.get("recommendations", []),
            "handoff_url": data.get("handoff_url") or data.get("handoffUrl"),
            "handoff_qr_url": data.get("handoff_qr_url") or data.get("handoffQrUrl"),
            "debug_target_url": target_url,
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Cloud retornou erro em {target_url}: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao conectar na cloud em {target_url}: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
