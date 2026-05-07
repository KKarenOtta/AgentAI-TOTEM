from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any

from core.persistence.jsonl_store import append_jsonl
from core.persistence.sync_queue import enqueue_sync


class MetricsLogger:
    def __init__(self, path: str = "data/metrics/metrics.jsonl"):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def save(self, metric: dict[str, Any]) -> None:
        append_jsonl(self.path, metric)

        try:
            enqueue_sync(
                entity="metrics",
                operation="insert",
                payload=metric,
                company_id=metric.get("company_id"),
                session_id=metric.get("session_id"),
            )
        except Exception:
            pass

    def load_rows(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []

        rows: list[dict[str, Any]] = []

        with open(self.path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue

        return rows

    def build_dashboard(self, company_id: str) -> dict[str, Any]:
        rows = self.load_rows()

        funnel = {
            "impressions": 0,
            "interactions": 0,
            "leads": 0,
            "issued": 0,
            "redeemed": 0,
        }

        nps_scores: list[int] = []

        campaigns = defaultdict(
            lambda: {
                "impressions": 0,
                "issued": 0,
                "redeemed": 0,
            }
        )

        for row in rows:
            if row.get("company_id") != company_id:
                continue

            event = row.get("event")

            if event == "campaign_impression":
                funnel["impressions"] += 1

                for cid in row.get("campaign_ids", []):
                    campaigns[cid]["impressions"] += 1

            elif event == "interaction":
                funnel["interactions"] += 1

            elif event == "lead_capture":
                funnel["leads"] += 1

            elif event == "coupon_issued":
                funnel["issued"] += 1

                cid = row.get("campaign_id")

                if cid:
                    campaigns[cid]["issued"] += 1

            elif event == "coupon_redeemed":
                funnel["redeemed"] += 1

                cid = row.get("campaign_id")

                if cid:
                    campaigns[cid]["redeemed"] += 1

            elif event in {"nps", "nps_submitted"}:
                if row.get("nps_score") is not None:
                    nps_scores.append(row["nps_score"])

        def rate(a: int, b: int) -> float:
            return round((a / b * 100), 2) if b else 0

        campaign_list: list[dict[str, Any]] = []

        for cid, data in campaigns.items():
            campaign_list.append(
                {
                    "campaign_id": cid,
                    "impressions": data["impressions"],
                    "issued": data["issued"],
                    "redeemed": data["redeemed"],
                    "ctr": rate(data["issued"], data["impressions"]),
                    "conversion": rate(data["redeemed"], data["issued"]),
                }
            )

        campaign_list.sort(key=lambda x: -x["conversion"])

        return {
            "funnel": funnel,
            "rates": {
                "ctr": rate(funnel["issued"], funnel["impressions"]),
                "lead_rate": rate(funnel["leads"], funnel["interactions"]),
                "conversion": rate(funnel["redeemed"], funnel["issued"]),
            },
            "nps": {
                "avg": round(sum(nps_scores) / len(nps_scores), 2)
                if nps_scores
                else 0,
                "count": len(nps_scores),
            },
            "campaigns": campaign_list,
        }
