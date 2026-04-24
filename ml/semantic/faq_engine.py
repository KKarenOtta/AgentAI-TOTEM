from __future__ import annotations

import json
from pathlib import Path

from ml.semantic.embeddings import embed, cosine

FAQ_FILE = Path("data/zoo_faq.json")
HISTORY_FILE = Path("data/conversation_history.jsonl")


class FAQEngine:
    def __init__(self):
        self.data = []
        self._load()

    def _load(self):
        if FAQ_FILE.exists():
            raw = json.loads(FAQ_FILE.read_text())
            for item in raw:
                self.data.append({
                    "question": item["question"],
                    "answer": item["answer"],
                    "embedding": embed(item["question"]),
                    "weight": 1.0
                })

        # histórico aumenta peso
        if HISTORY_FILE.exists():
            for line in HISTORY_FILE.read_text().splitlines():
                entry = json.loads(line)
                if entry.get("score", 0) > 0.7:
                    self.data.append({
                        "question": entry["question"],
                        "answer": entry["answer"],
                        "embedding": embed(entry["question"]),
                        "weight": 1.5
                    })

    def search(self, query, intent):
        q_emb = embed(query)

        best = None
        best_score = 0

        for item in self.data:
            sim = cosine(q_emb, item["embedding"])
            score = sim * item["weight"]

            if score > best_score:
                best_score = score
                best = item

        if best and best_score > 0.5:
            return best["answer"], best_score

        return "", best_score
