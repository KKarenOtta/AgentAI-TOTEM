from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = os.getenv("SEMANTIC_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
STORE_PATH = Path(os.getenv("SEMANTIC_EMBEDDINGS_PATH", "data/semantic/embeddings.jsonl"))

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def text_hash(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def embed(text: str) -> list[float]:
    normalized = normalize_text(text)

    if not normalized:
        return []

    vector = _get_model().encode(normalized)
    return [float(x) for x in vector]


def cosine(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    if a is None or b is None:
        return 0.0

    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)

    if va.size == 0 or vb.size == 0:
        return 0.0

    denominator = float(np.linalg.norm(va) * np.linalg.norm(vb))

    if denominator == 0 or math.isnan(denominator):
        return 0.0

    return float(np.dot(va, vb) / denominator)


def _ensure_store() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not STORE_PATH.exists():
        STORE_PATH.write_text("", encoding="utf-8")


def load_store() -> list[dict[str, Any]]:
    _ensure_store()

    rows: list[dict[str, Any]] = []

    with STORE_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(row, dict):
                rows.append(row)

    return rows


def save_store(rows: list[dict[str, Any]]) -> None:
    _ensure_store()

    with STORE_PATH.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def upsert_embedding(
    *,
    company_id: str,
    namespace: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_text(text)

    if not company_id:
        raise ValueError("company_id é obrigatório.")

    if not namespace:
        raise ValueError("namespace é obrigatório.")

    if not normalized:
        raise ValueError("text é obrigatório.")

    row_id = f"{company_id}:{namespace}:{text_hash(normalized)}"
    rows = load_store()

    existing = None
    next_rows = []

    for row in rows:
        if row.get("id") == row_id:
            existing = row
            continue
        next_rows.append(row)

    vector = existing.get("embedding") if existing else None
    if not vector:
        vector = embed(normalized)

    row = {
        "id": row_id,
        "company_id": company_id,
        "namespace": namespace,
        "text": normalized,
        "embedding": vector,
        "metadata": metadata or {},
    }

    next_rows.append(row)
    save_store(next_rows)

    return row


def search_embeddings(
    *,
    company_id: str,
    namespace: str | None,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    query_vector = embed(query)

    if not query_vector:
        return []

    results = []

    for row in load_store():
        if row.get("company_id") != company_id:
            continue

        if namespace and row.get("namespace") != namespace:
            continue

        score = cosine(query_vector, row.get("embedding") or [])

        if score < min_score:
            continue

        results.append(
            {
                "score": round(score, 4),
                "text": row.get("text"),
                "metadata": row.get("metadata") or {},
                "namespace": row.get("namespace"),
                "id": row.get("id"),
            }
        )

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]
