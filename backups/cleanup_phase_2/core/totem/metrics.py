import json
import os
from collections import defaultdict
from typing import Any


class MetricsLogger:
    def __init__(self, path: str = "data/metrics/metrics.jsonl"):
        self.path = path
        dir_name = os.path.dirname(self.path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def save(self, metric: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric, ensure_ascii=False) + "\n")

    def load_rows(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []

        rows: list[dict] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
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

        leads = 0
        issued = 0
        redeemed = 0

        campaigns = defaultdict(lambda: {
            "issued": 0,
            "redeemed": 0,
        })

        stores = defaultdict(lambda: {
            "redeemed": 0,
        })

        for row in rows:
            if row.get("event") == "lead_capture" and row.get("company_id") == company_id:
                leads += 1

            elif row.get("event") == "coupon_issued" and row.get("company_id") == company_id:
                issued += 1
                campaign_id = row.get("campaign_id")
                if campaign_id:
                    campaigns[campaign_id]["issued"] += 1

            elif row.get("event") == "coupon_redeemed" and row.get("company_id") == company_id:
                redeemed += 1

                campaign_id = row.get("campaign_id")
                if campaign_id:
                    campaigns[campaign_id]["redeemed"] += 1

                store_id = row.get("store_id") or "unknown"
                stores[store_id]["redeemed"] += 1

        conversion = (redeemed / issued * 100) if issued else 0

        campaign_list = []
        for campaign_id, data in campaigns.items():
            campaign_conversion = (
                data["redeemed"] / data["issued"] * 100
                if data["issued"] else 0
            )
            campaign_list.append(
                {
                    "campaign_id": campaign_id,
                    "issued": data["issued"],
                    "redeemed": data["redeemed"],
                    "conversion": round(campaign_conversion, 2),
                }
            )

        campaign_list.sort(key=lambda item: (-item["conversion"], item["campaign_id"]))

        store_list = []
        for store_id, data in stores.items():
            store_list.append(
                {
                    "store_id": store_id,
                    "redeemed": data["redeemed"],
                }
            )

        store_list.sort(key=lambda item: (-item["redeemed"], item["store_id"]))

        return {
            "kpis": {
                "leads": leads,
                "issued": issued,
                "redeemed": redeemed,
                "conversion": round(conversion, 2),
            },
            "campaigns": campaign_list,
            "stores": store_list,
        }

    def build_report(self, out_path: str = "data/metrics/metrics_report.md") -> None:
        rows = self.load_rows()
        total = len(rows)

        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        if total == 0:
            content = "# Relatório de Métricas do Totem\n\nNenhum evento registrado.\n"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            return

        lines = []
        lines.append("# Relatório de Métricas do Totem\n\n")
        lines.append(f"- Total de eventos: **{total}**\n")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
