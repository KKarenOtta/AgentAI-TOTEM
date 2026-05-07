from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from core.faq.store import load_faq
from ml.semantic.embeddings import upsert_embedding

METRICS_PATH = Path("data/metrics/metrics.jsonl")
CANDIDATES_PATH = Path("data/faq_candidates.json")
REPORT_PATH = Path("data/training/continuous_training_report.json")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
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


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _interaction_rows(company_id: str | None = None) -> list[dict[str, Any]]:
    rows = []

    for row in _read_jsonl(METRICS_PATH):
        if row.get("event") != "interaction":
            continue

        if company_id and row.get("company_id") != company_id:
            continue

        question = _clean_text(row.get("question"))
        answer = _clean_text(row.get("response"))
        score = float(row.get("score") or 0)

        if not question or not answer:
            continue

        rows.append(
            {
                "company_id": row.get("company_id") or company_id or "default",
                "session_id": row.get("session_id"),
                "question": question,
                "answer": answer,
                "score": score,
                "response_source": row.get("response_source"),
                "matched_question": row.get("matched_question"),
                "latency": row.get("latency"),
            }
        )

    return rows


def index_faq(company_id: str) -> int:
    count = 0

    for item in load_faq(company_id):
        question = _clean_text(item.get("question"))
        answer = _clean_text(item.get("answer"))

        if not question or not answer:
            continue

        upsert_embedding(
            company_id=company_id,
            namespace="faq",
            text=question,
            metadata={
                "answer": answer,
                "intent": item.get("intent"),
                "uses": item.get("uses") or 0,
                "quality_score": item.get("score") or 0,
                "source": "faq",
            },
        )

        count += 1

    return count


def index_interactions(company_id: str | None = None, min_score: float = 0.55) -> int:
    count = 0

    for row in _interaction_rows(company_id):
        if row["score"] < min_score:
            continue

        upsert_embedding(
            company_id=row["company_id"],
            namespace="interaction",
            text=row["question"],
            metadata={
                "answer": row["answer"],
                "session_id": row.get("session_id"),
                "score": row["score"],
                "response_source": row.get("response_source"),
                "matched_question": row.get("matched_question"),
                "latency": row.get("latency"),
            },
        )

        count += 1

    return count


def generate_faq_candidates(company_id: str | None = None, min_count: int = 2, min_score: float = 0.65) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in _interaction_rows(company_id):
        if row["score"] < min_score:
            continue

        key = row["question"].strip().lower()
        buckets[key].append(row)

    candidates = []

    for question, rows in buckets.items():
        if len(rows) < min_count:
            continue

        answers = [row["answer"] for row in rows if row.get("answer")]
        if not answers:
            continue

        best_answer = Counter(answers).most_common(1)[0][0]
        sample = rows[-1]

        candidates.append(
            {
                "company_id": sample["company_id"],
                "question": question,
                "answer": best_answer,
                "count": len(rows),
                "avg_score": round(sum(row["score"] for row in rows) / len(rows), 4),
                "source": "continuous_training",
                "status": "pending_review",
            }
        )

    CANDIDATES_PATH.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return candidates


def build_campaign_weights(company_id: str | None = None) -> dict[str, Any]:
    stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "impressions": 0,
            "issued": 0,
            "redeemed": 0,
            "leads": 0,
            "interactions": 0,
        }
    )

    for row in _read_jsonl(METRICS_PATH):
        if company_id and row.get("company_id") != company_id:
            continue

        event = row.get("event")

        if event == "interaction":
            session_id = row.get("session_id") or "_global"
            stats[session_id]["interactions"] += 1

        if event == "lead_capture":
            session_id = row.get("session_id") or "_global"
            stats[session_id]["leads"] += 1

        if event == "campaign_impression":
            for campaign_id in row.get("campaign_ids") or []:
                stats[campaign_id]["impressions"] += 1

        if event == "coupon_issued":
            campaign_id = row.get("campaign_id")
            if campaign_id:
                stats[campaign_id]["issued"] += 1

        if event == "coupon_redeemed":
            campaign_id = row.get("campaign_id")
            if campaign_id:
                stats[campaign_id]["redeemed"] += 1

    campaign_weights = {}

    for key, values in stats.items():
        impressions = values["impressions"]
        issued = values["issued"]
        redeemed = values["redeemed"]

        ctr = issued / impressions if impressions else 0
        conversion = redeemed / issued if issued else 0

        campaign_weights[key] = {
            "weight": round(1.0 + ctr + conversion * 2.0, 4),
            "ctr": round(ctr, 4),
            "conversion": round(conversion, 4),
            "raw": values,
        }

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "company_id": company_id,
        "campaign_weights": campaign_weights,
    }

    Path("data/recommender").mkdir(parents=True, exist_ok=True)
    Path("data/recommender/campaign_weights.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return out


def run_continuous_training(company_id: str | None = None) -> dict[str, Any]:
    companies = set()

    if company_id:
        companies.add(company_id)
    else:
        for row in _interaction_rows():
            if row.get("company_id"):
                companies.add(row["company_id"])

    faq_indexed = 0
    for cid in sorted(companies):
        faq_indexed += index_faq(cid)

    interactions_indexed = index_interactions(company_id=company_id)
    candidates = generate_faq_candidates(company_id=company_id)
    campaign_weights = build_campaign_weights(company_id=company_id)

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "company_id": company_id,
        "companies": sorted(companies),
        "faq_embeddings_indexed": faq_indexed,
        "interaction_embeddings_indexed": interactions_indexed,
        "faq_candidates": len(candidates),
        "campaign_weights_count": len(campaign_weights.get("campaign_weights") or {}),
        "status": "ok",
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return report


if __name__ == "__main__":
    result = run_continuous_training()
    print(json.dumps(result, ensure_ascii=False, indent=2))
