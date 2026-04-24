import json
import os
from typing import List, Dict, Any

DEFAULT_PATH = os.getenv("COMPANIES_DB_PATH", "data/companies.json")


def _ensure_file(path: str) -> None:
    dir_ = os.path.dirname(path)
    if dir_:
        os.makedirs(dir_, exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_companies(path: str = DEFAULT_PATH) -> List[Dict[str, Any]]:
    _ensure_file(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, list) else []


def save_companies(companies: List[Dict[str, Any]], path: str = DEFAULT_PATH) -> None:
    _ensure_file(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)


def add_company(company_id: str, name: str, path: str = DEFAULT_PATH) -> None:
    company_id = company_id.strip()
    name = name.strip()

    if not company_id or not name:
        return

    companies = load_companies(path)

    if any(c.get("company_id") == company_id for c in companies):
        return

    companies.append({
        "company_id": company_id,
        "name": name
    })
    save_companies(companies, path)


def delete_company(company_id: str, path: str = DEFAULT_PATH) -> None:
    companies = load_companies(path)
    companies = [c for c in companies if c.get("company_id") != company_id]
    save_companies(companies, path)