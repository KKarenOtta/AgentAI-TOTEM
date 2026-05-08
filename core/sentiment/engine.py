from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


POSITIVE_WORDS = {
    "bom", "boa", "ótimo", "otimo", "excelente", "rápido", "rapido",
    "gostei", "útil", "util", "perfeito", "satisfeito", "recomendo",
}

NEGATIVE_WORDS = {
    "ruim", "péssimo", "pessimo", "demora", "demorou", "lento",
    "problema", "erro", "falha", "fraco", "insatisfeito", "horrível",
    "horrivel", "não gostei", "nao gostei",
}

FRUSTRATION_WORDS = {
    "demora", "demorou", "lento", "erro", "falha", "problema",
    "não funciona", "nao funciona", "travou", "ninguém", "ninguem",
}


@lru_cache(maxsize=1)
def _vader() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


@lru_cache(maxsize=1)
def _transformer_pipeline():
    if os.getenv("SENTIMENT_TRANSFORMERS_ENABLED", "true").lower() not in {"1", "true", "yes"}:
        return None

    try:
        from transformers import pipeline

        model_name = os.getenv(
            "SENTIMENT_MODEL",
            "nlptown/bert-base-multilingual-uncased-sentiment",
        )

        return pipeline("sentiment-analysis", model=model_name)
    except Exception:
        return None


def _normalize(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def _score_from_words(text: str) -> float:
    value = _normalize(text)

    if not value:
        return 0.0

    positive = sum(1 for word in POSITIVE_WORDS if word in value)
    negative = sum(1 for word in NEGATIVE_WORDS if word in value)

    raw = positive - negative

    if raw == 0:
        return 0.0

    return max(-1.0, min(1.0, raw / 3))


def _label_from_score(score: float) -> str:
    if score >= 0.25:
        return "positive"
    if score <= -0.25:
        return "negative"
    return "neutral"


def _nps_class(score: int | None) -> str:
    if score is None:
        return "unknown"
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def _frustration_risk(text: str, sentiment_score: float, nps_score: int | None) -> str:
    value = _normalize(text)
    has_frustration = any(word in value for word in FRUSTRATION_WORDS)

    if has_frustration or sentiment_score <= -0.55 or (nps_score is not None and nps_score <= 4):
        return "high"

    if sentiment_score <= -0.25 or (nps_score is not None and nps_score <= 6):
        return "medium"

    return "low"


def _transformer_result(text: str) -> dict[str, Any]:
    pipe = _transformer_pipeline()

    if not pipe or not text:
        return {}

    try:
        result = pipe(text[:512])[0]
    except Exception:
        return {}

    return {
        "transformer_label": result.get("label"),
        "transformer_score": round(float(result.get("score") or 0), 4),
    }


def analyze_sentiment(
    text: str | None,
    *,
    nps_score: int | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    original = text or ""
    normalized = _normalize(original)

    vader_score = 0.0
    try:
        vader_score = float(_vader().polarity_scores(original).get("compound") or 0.0)
    except Exception:
        vader_score = 0.0

    word_score = _score_from_words(normalized)

    if normalized:
        sentiment_score = round((vader_score * 0.55) + (word_score * 0.45), 4)
    elif nps_score is not None:
        sentiment_score = round((nps_score - 5) / 5, 4)
    else:
        sentiment_score = 0.0

    sentiment_score = max(-1.0, min(1.0, sentiment_score))
    label = _label_from_score(sentiment_score)

    payload = {
        "text": original,
        "sentiment": label,
        "sentiment_score": sentiment_score,
        "nps_class": _nps_class(nps_score),
        "frustration_risk": _frustration_risk(normalized, sentiment_score, nps_score),
        "engagement_score": round(min(1.0, max(0.0, len(normalized) / 180)), 4),
        "context": context or {},
    }

    payload.update(_transformer_result(original))

    return payload
