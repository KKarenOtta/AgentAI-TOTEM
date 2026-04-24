from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import time

from infra.realtime.event_bus import get_queue

router = APIRouter()

@router.get("/events/{company_id}")
def events(company_id: str):

    def event_stream():
        q = get_queue(company_id)

        while True:
            try:
                data = q.get(timeout=30)
                yield f"data: {json.dumps(data)}\n\n"
            except Exception:
                yield "data: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
