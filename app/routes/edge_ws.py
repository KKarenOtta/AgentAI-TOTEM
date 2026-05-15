from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.edge_push import connect, disconnect

router = APIRouter()

@router.websocket("/ws/session/{session_id}")
async def session_ws(websocket: WebSocket, session_id: str):
    await connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect(session_id, websocket)
