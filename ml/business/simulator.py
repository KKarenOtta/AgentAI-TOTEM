from __future__ import annotations

import json
import random
from pathlib import Path

OUT_DIR = Path("data/ml/business/datasets")


def simulate_coupon_dataset(company_id: str, n: int = 300) -> Path:
    random.seed(42)

    campaigns = [
        {"campaign_id": "CAMP-001", "discount_value": 0, "base_rate": 0.05},
        {"campaign_id": "CAMP-F53872", "discount_value": 15, "base_rate": 0.18},
        {"campaign_id": "CAMP-DDEBF7", "discount_value": 45, "base_rate": 0.32},
    ]

    rows = []

    for _ in range(n):
        campaign = random.choice(campaigns)
        hour = random.randint(8, 22)
        has_discount = 1 if campaign["discount_value"] > 0 else 0

        probability = campaign["base_rate"]

        if 11 <= hour <= 14:
            probability += 0.06

        if 18 <= hour <= 21:
            probability += 0.04

        label = 1 if random.random() < probability else 0

        rows.append(
            {
                "company_id": company_id,
                "campaign_id": campaign["campaign_id"],
                "discount_value": campaign["discount_value"],
                "has_discount": has_discount,
                "hour": hour,
                "label": label,
                "source": "simulated",
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{company_id}_simulated.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    positives = sum(row["label"] for row in rows)
    negatives = len(rows) - positives

    print(f"[SIMULATED] total={len(rows)} positives={positives} negatives={negatives}")
    return out


if __name__ == "__main__":
    print(simulate_coupon_dataset("FLX-001"))
