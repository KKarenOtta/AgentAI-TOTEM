from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"


@dataclass
class SentimentResult:
    sentiment: str
    sentiment_score: float
    frustration_risk: str
    churn_risk: str
    model: str
    raw: dict[str, Any]


_pipeline = None


def _load_pipeline():
    global _pipeline

    if _pipeline is not None:
        return _pipeline

    try:
        from transformers import pipeline

        _pipeline = pipeline("sentiment-analysis", model=MODEL_NAME)
        return _pipeline
    except Exception:
        _pipeline = False
        return None


def _fallback_score(text: str) -> float:
    value = (text or "").lower()

    negative = ["ruim", "péssimo", "horrível", "demora", "problema", "não gostei", "fraco", "lento"]
    positive = ["bom", "ótimo", "excelente", "adorei", "gostei", "rápido", "perfeito"]

    score = 0.0
    for term in positive:
        if term in value:
            score += 0.2
    for term in negative:
        if term in value:
            score -= 0.25

    return max(-1.0, min(1.0, score))


def _classify(score: float) -> str:
    if score >= 0.25:
        return "positive"
    if score <= -0.25:
        return "negative"
    return "neutral"


def analyze_sentiment(text: str, nps_score: int | None = None) -> SentimentResult:
    text = (text or "").strip()
    raw: dict[str, Any] = {}

    pipe = _load_pipeline()

    if pipe:
        try:
            result = pipe(text[:512])[0]
            raw = dict(result)

            label = str(result.get("label") or "")
            stars = int(label[0]) if label and label[0].isdigit() else 3
            score = (stars - 3) / 2
            model = MODEL_NAME
        except Exception:
            score = _fallback_score(text)
            model = "lexicon_fallback"
    else:
        score = _fallback_score(text)
        model = "lexicon_fallback"

    if nps_score is not None:
        if nps_score <= 6:
            score = min(score, -0.35)
        elif nps_score >= 9:
            score = max(score, 0.35)

    sentiment = _classify(score)

    frustration_risk = "high" if score <= -0.5 else "medium" if score <= -0.2 else "low"
    churn_risk = "high" if nps_score is not None and nps_score <= 6 else "medium" if sentiment == "negative" else "low"

    return SentimentResult(
        sentiment=sentiment,
        sentiment_score=round(float(score), 4),
        frustration_risk=frustration_risk,
        churn_risk=churn_risk,
        model=model,
        raw=raw,
    )


def analyze_nps_file(company_id: str | None = None) -> dict[str, Any]:
    input_path = Path("data/nps/nps.jsonl")
    output_path = Path("data/sentiment/nps_sentiment.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        return {"processed": 0, "output": str(output_path)}

    processed = 0

    with input_path.open("r", encoding="utf-8") as src, output_path.open("a", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if company_id and row.get("company_id") != company_id:
                continue

            comment = row.get("comment") or row.get("text") or ""
            score = row.get("score") or row.get("nps_score")

            try:
                score_int = int(score)
            except Exception:
                score_int = None

            result = analyze_sentiment(comment, score_int)

            out = {
                **row,
                "sentiment": result.sentiment,
                "sentiment_score": result.sentiment_score,
                "frustration_risk": result.frustration_risk,
                "churn_risk": result.churn_risk,
                "sentiment_model": result.model,
            }

            dst.write(json.dumps(out, ensure_ascii=False) + "\n")
            processed += 1

    return {"processed": processed, "output": str(output_path)}


if __name__ == "__main__":
    print(json.dumps(analyze_nps_file(), ensure_ascii=False, indent=2))
