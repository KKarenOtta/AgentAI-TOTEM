from __future__ import annotations

from collections import defaultdict
import json
import os

METRICS_PATH = "data/metrics/metrics.jsonl"


def load_campaign_performance():
    stats = defaultdict(lambda: {"issued": 0, "redeemed": 0})

    if not os.path.exists(METRICS_PATH):
        return stats

    with open(METRICS_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except Exception:
                continue

            cid = row.get("campaign_id")
            if not cid:
                continue

            if row.get("event") == "coupon_issued":
                stats[cid]["issued"] += 1

            elif row.get("event") == "coupon_redeemed":
                stats[cid]["redeemed"] += 1

    return stats


PERF = load_campaign_performance()


def score_campaign(campaign, profile, intent):
    base = 1.0

    cid = campaign.get("campaign_id")
    perf = PERF.get(cid, {})

    issued = perf.get("issued", 0)
    redeemed = perf.get("redeemed", 0)

    conversion = (redeemed / issued) if issued else 0

    score = base + (conversion * 3)

    return round(score, 3), f"conversion={conversion:.2f}"
