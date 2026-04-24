from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

LOG_FILE = Path("data/feedback.jsonl")
FAQ_FILE = Path("data/zoo_faq.json")
CANDIDATES_FILE = Path("data/faq_candidates.json")


def load_logs():
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_candidates(min_count: int = 3):
    logs = load_logs()

    counter = defaultdict(list)

    for entry in logs:
        if not entry.get("success"):
            continue

        q = entry.get("question", "").strip().lower()
        a = entry.get("answer", "").strip()

        if q and a:
            counter[q].append(a)

    candidates = []

    for question, answers in counter.items():
        if len(answers) >= min_count:
            # resposta mais frequente
            best_answer = max(set(answers), key=answers.count)

            candidates.append({
                "question": question,
                "answer": best_answer,
                "count": len(answers),
                "status": "pending_review"
            })

    CANDIDATES_FILE.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return candidates


if __name__ == "__main__":
    result = generate_candidates()
    print(f"{len(result)} candidatos gerados em {CANDIDATES_FILE}")
