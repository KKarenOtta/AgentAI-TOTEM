import json
from pathlib import Path

DATA_PATH = Path("data/company_profiles.json")


def load_company_context(company_id: str) -> dict:
    if not DATA_PATH.exists():
        return {}

    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return data.get(company_id, {})
    except Exception:
        return {}
