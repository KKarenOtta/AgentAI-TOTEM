from __future__ import annotations

import json
from pathlib import Path

LOG_FILE = Path("data/feedback.jsonl")


def log_feedback(question: str, answer: str, success: bool, score: float):
    entry = {
        "question": question,
        "answer": answer,
        "success": success,
        "score": score
    }

    LOG_FILE.parent.mkdir(exist_ok=True)

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
