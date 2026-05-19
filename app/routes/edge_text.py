from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config.runtime import CLOUD_BASE_URL
from app.services.edge_push import publish

router = APIRouter()


class EdgeInteractRequest(BaseModel):
    company_id: str
    session_id: str
    message: str = ""


@router.post("/edge/interact/text")
async def edge_interact_text(payload: EdgeInteractRequest):
    if not CLOUD_BASE_URL:
        raise HTTPException(status_code=500, detail="CLOUD_BASE_URL nao configurado.")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{CLOUD_BASE_URL}/cloud/interact",
                data={
                    "company_id": payload.company_id,
                    "session_id": payload.session_id,
                    "message": payload.message or "",
                },
            )

        response.raise_for_status()
        result = response.json()

        await publish(payload.session_id, result)

        return {
            "status": "ok",
            "session_id": payload.session_id,
            "cloud_result": result,
        }

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Cloud retornou erro: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao conectar na cloud: {str(exc)}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
