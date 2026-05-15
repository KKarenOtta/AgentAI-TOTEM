from collections import defaultdict

from fastapi import WebSocket


_connections: dict[str, list[WebSocket]] = defaultdict(list)


async def connect(session_id: str, websocket: WebSocket):
    await websocket.accept()
    _connections[session_id].append(websocket)


def disconnect(session_id: str, websocket: WebSocket):
    if session_id in _connections and websocket in _connections[session_id]:
        _connections[session_id].remove(websocket)

        if not _connections[session_id]:
            del _connections[session_id]


async def publish(session_id: str, data: dict):
    dead_connections = []

    for websocket in list(_connections.get(session_id, [])):
        try:
            await websocket.send_json(data)
        except Exception:
            dead_connections.append(websocket)

    for websocket in dead_connections:
        disconnect(session_id, websocket)
