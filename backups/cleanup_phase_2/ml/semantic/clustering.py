from __future__ import annotations

import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

LOG_FILE = Path("data/feedback.jsonl")
OUTPUT_FILE = Path("data/question_clusters.json")


def load_questions():
    if not LOG_FILE.exists():
        return []

    with LOG_FILE.open(encoding="utf-8") as f:
        return [json.loads(line)["question"] for line in f if line.strip()]


def cluster_questions(n_clusters: int = 5):
    questions = load_questions()

    if len(questions) < n_clusters:
        return []

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(questions)

    model = KMeans(n_clusters=n_clusters, random_state=42)
    labels = model.fit_predict(X)

    clusters = {}

    for q, label in zip(questions, labels):
        clusters.setdefault(int(label), []).append(q)

    OUTPUT_FILE.write_text(
        json.dumps(clusters, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return clusters


if __name__ == "__main__":
    result = cluster_questions()
    print(f"{len(result)} clusters gerados")
