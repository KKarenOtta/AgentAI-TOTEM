from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib


MODEL_DIR = Path("data/ml/intent/models")
LABEL_MAP_PATH = Path("data/ml/intent/label_map.json")

_ENCODER: Any = None
_CLASSIFIER: Any = None
_REVERSE_MAP: dict[int, str] | None = None


def is_available() -> bool:
    return (
        (MODEL_DIR / "embedding_model").exists()
        and (MODEL_DIR / "intent_classifier.joblib").exists()
        and LABEL_MAP_PATH.exists()
    )


def _load():
    global _ENCODER, _CLASSIFIER, _REVERSE_MAP

    if _ENCODER is not None and _CLASSIFIER is not None and _REVERSE_MAP is not None:
        return _ENCODER, _CLASSIFIER, _REVERSE_MAP

    if not is_available():
        raise FileNotFoundError("Modelo de intenção ainda não treinado.")

    from sentence_transformers import SentenceTransformer

    label_map = json.loads(LABEL_MAP_PATH.read_text(encoding="utf-8"))

    _ENCODER = SentenceTransformer(str(MODEL_DIR / "embedding_model"))
    _CLASSIFIER = joblib.load(MODEL_DIR / "intent_classifier.joblib")
    _REVERSE_MAP = {int(value): key for key, value in label_map.items()}

    return _ENCODER, _CLASSIFIER, _REVERSE_MAP


def predict(text: str) -> tuple[str | None, float]:
    clean_text = (text or "").strip()

    if not clean_text or not is_available():
        return None, 0.0

    encoder, classifier, reverse_map = _load()

    embedding = encoder.encode([clean_text], normalize_embeddings=True)
    probabilities = classifier.predict_proba(embedding)[0]

    best_index = int(probabilities.argmax())
    confidence = round(float(probabilities[best_index]), 4)

    return reverse_map[best_index], confidence
