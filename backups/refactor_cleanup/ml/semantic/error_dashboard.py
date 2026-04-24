from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

LOG_FILE = Path("data/feedback.jsonl")
OUTPUT_FILE = Path("data/error_dashboard.json")


def build_dashboard():
    if not LOG_FILE.exists():
        return {}

    with LOG_FILE.open(encoding="utf-8") as f:
        logs = [json.loads(line) for line in f if line.strip()]

    failures = [l for l in logs if not l.get("success")]

    questions = [f["question"] for f in failures]

    most_common = Counter(questions).most_common(20)

    dashboard = {
        "total_logs": len(logs),
        "failures": len(failures),
        "top_errors": most_common,
    }

    OUTPUT_FILE.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return dashboard


if __name__ == "__main__":
    result = build_dashboard()
    print("Dashboard atualizado")
