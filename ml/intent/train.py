from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split


DATA_PATH = Path("data/ml/intent/dataset.jsonl")
MODEL_DIR = Path("data/ml/intent/models")
REPORT_DIR = Path("data/ml/intent/reports")
LABEL_MAP_PATH = Path("data/ml/intent/label_map.json")

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def load_rows() -> list[dict[str, str]]:
    rows = []

    for line in DATA_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        item = json.loads(line)
        text = str(item.get("text") or "").strip()
        intent = str(item.get("intent") or "").strip()

        if text and intent:
            rows.append({"text": text, "intent": intent})

    if len(rows) < 12:
        raise RuntimeError("Dataset insuficiente para treino supervisionado.")

    return rows


def train() -> dict[str, Any]:
    rows = load_rows()

    texts = [row["text"] for row in rows]
    labels = [row["intent"] for row in rows]

    label_names = sorted(set(labels))
    label_map = {label: index for index, label in enumerate(label_names)}
    y = [label_map[label] for label in labels]

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    train_embeddings = encoder.encode(x_train, normalize_embeddings=True)
    test_embeddings = encoder.encode(x_test, normalize_embeddings=True)

    classifier = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )

    classifier.fit(train_embeddings, y_train)

    predictions = classifier.predict(test_embeddings)
    probabilities = classifier.predict_proba(test_embeddings)

    report_dict = classification_report(
        y_test,
        predictions,
        target_names=label_names,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(y_test, predictions)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    encoder.save(str(MODEL_DIR / "embedding_model"))
    joblib.dump(classifier, MODEL_DIR / "intent_classifier.joblib")

    LABEL_MAP_PATH.write_text(
        json.dumps(label_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(
        matrix,
        index=label_names,
        columns=label_names,
    ).to_csv(REPORT_DIR / "confusion_matrix.csv", encoding="utf-8")

    report = {
        "approach": "transfer_learning_sentence_embeddings_plus_logistic_regression",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "classifier": "LogisticRegression",
        "total_rows": len(rows),
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "labels": label_map,
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "macro_precision": round(float(report_dict["macro avg"]["precision"]), 4),
        "macro_recall": round(float(report_dict["macro avg"]["recall"]), 4),
        "macro_f1": round(float(report_dict["macro avg"]["f1-score"]), 4),
        "weighted_precision": round(float(report_dict["weighted avg"]["precision"]), 4),
        "weighted_recall": round(float(report_dict["weighted avg"]["recall"]), 4),
        "weighted_f1": round(float(report_dict["weighted avg"]["f1-score"]), 4),
        "classification_report": report_dict,
        "test_predictions": [
            {
                "text": text,
                "expected": label_names[expected],
                "predicted": label_names[predicted],
                "confidence": round(float(max(prob)), 4),
            }
            for text, expected, predicted, prob in zip(
                x_test,
                y_test,
                predictions,
                probabilities,
            )
        ],
    }

    (REPORT_DIR / "training_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    train()
