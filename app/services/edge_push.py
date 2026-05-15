from collections import defaultdict
from fastapi import WebSocket

_connections = defaultdict(list)

async def connect(session_id: str, websocket: WebSocket):
    await websocket.accept()
    _connections[session_id].append(websocket)

def disconnect(session_id: str, websocket: WebSocket):
    if websocket in _connections[session_id]:
        _connections[session_id].remove(websocket)

async def publish(session_id: str, data: dict):
    dead = []
    for ws in list(_connections[session_id]):
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(ws)

    for ws in dead:
        disconnect(session_id, ws)
