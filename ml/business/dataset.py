from __future__ import annotations

import json
from pathlib import Path

COUPONS_PATH = Path("data/coupons/coupons.jsonl")


def load_coupons():
    if not COUPONS_PATH.exists():
        return []

    rows = []
    with COUPONS_PATH.open() as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                continue
    return rows


def normalize_status(r: dict) -> int:
    status = str(r.get("status", "")).lower().strip()

    if status == "redeemed":
        return 1

    # fallback: campo redeemed_at
    if r.get("redeemed_at"):
        return 1

    return 0


def build_training_dataset(company_id: str):
    rows = load_coupons()

    samples = []
    positives = 0
    negatives = 0

    for r in rows:
        if r.get("company_id") != company_id:
            continue

        label = normalize_status(r)

        if label == 1:
            positives += 1
        else:
            negatives += 1

        sample = {
            "campaign_id": r.get("campaign_id"),
            "discount_value": r.get("discount_value", 0),
            "has_discount": 1 if r.get("discount_value", 0) > 0 else 0,
            "label": label,
        }

        samples.append(sample)

    print(f"[DATASET] total={len(samples)} positives={positives} negatives={negatives}")

    return samples


def save_dataset(company_id: str):
    data = build_training_dataset(company_id)

    out = Path(f"data/ml/business/datasets/{company_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(json.dumps(data, indent=2))
    return out
