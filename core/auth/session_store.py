import json
import uuid
from pathlib import Path
from datetime import datetime

SESSIONS_FILE = Path("data/sessions.json")

def _load():
    if not SESSIONS_FILE.exists():
        return {}
    return json.loads(SESSIONS_FILE.read_text())

def _save(data):
    SESSIONS_FILE.write_text(json.dumps(data, indent=2))

def create_session(user: dict) -> str:
    sessions = _load()

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "user": user,
        "created_at": datetime.utcnow().isoformat()
    }

    _save(sessions)
    return session_id

def get_session(session_id: str):
    sessions = _load()
    return sessions.get(session_id)

def delete_session(session_id: str):
    sessions = _load()
    sessions.pop(session_id, None)
    _save(sessions)
