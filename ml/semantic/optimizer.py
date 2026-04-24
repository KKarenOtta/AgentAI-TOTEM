import json
from pathlib import Path

HISTORY = Path("data/conversation_history.jsonl")
CONFIG = Path("data/semantic_config.json")


def optimize():
    if not HISTORY.exists():
        return

    scores = []
    for line in HISTORY.read_text().splitlines():
        data = json.loads(line)
        scores.append(data.get("score", 0))

    if not scores:
        return

    avg = sum(scores) / len(scores)

    if avg < 0.5:
        threshold = 0.4
    elif avg > 0.8:
        threshold = 0.6
    else:
        threshold = 0.5

    CONFIG.write_text(json.dumps({"threshold": threshold}, indent=2))
