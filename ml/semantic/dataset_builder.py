import json
from pathlib import Path

SRC = Path("data/conversation_history.jsonl")
OUT = Path("data/training_dataset.json")


def build():
    data = []

    for line in SRC.read_text().splitlines():
        item = json.loads(line)

        if item["score"] > 0.7:
            data.append({
                "input": item["question"],
                "output": item["answer"]
            })

    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    build()
