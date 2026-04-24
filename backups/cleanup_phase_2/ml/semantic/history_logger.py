import json
from pathlib import Path

LOG = Path("data/conversation_history.jsonl")

def log_turn(session_id, question, answer, score):
    LOG.parent.mkdir(exist_ok=True)

    entry = {
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "score": score
    }

    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
