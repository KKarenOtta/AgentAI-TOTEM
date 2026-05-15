from pathlib import Path

RECORDINGS_DIR = Path("data/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

def record_question(session_id: str) -> str:
    out = RECORDINGS_DIR / f"{session_id}.wav"
    return str(out)
