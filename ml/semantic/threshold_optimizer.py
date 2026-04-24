from __future__ import annotations

import json
from pathlib import Path

LOG_FILE = Path("data/feedback.jsonl")
CONFIG_FILE = Path("data/semantic_config.json")


def optimize():
    if not LOG_FILE.exists():
        return 0.45

    with LOG_FILE.open(encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    if not logs:
        return 0.45

    success_rate = sum(1 for l in logs if l.get("success")) / len(logs)

    # ajuste simples
    if success_rate < 0.6:
        threshold = 0.35
    elif success_rate > 0.85:
        threshold = 0.55
    else:
        threshold = 0.45

    CONFIG_FILE.write_text(
        json.dumps({"threshold": threshold}, indent=2),
        encoding="utf-8"
    )

    return threshold


if __name__ == "__main__":
    t = optimize()
    print(f"Novo threshold: {t}")
