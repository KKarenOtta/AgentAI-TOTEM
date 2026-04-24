import json
from pathlib import Path

LOG = Path("data/conversation_history.jsonl")
OUT = Path("data/quality_report.json")


def evaluate():
    if not LOG.exists():
        return

    data = [json.loads(l) for l in LOG.read_text().splitlines()]

    total = len(data)
    high = len([d for d in data if d["score"] > 0.7])
    low = len([d for d in data if d["score"] < 0.4])

    report = {
        "total": total,
        "high_quality": high,
        "low_quality": low,
        "quality_rate": high / total if total else 0
    }

    OUT.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    evaluate()
