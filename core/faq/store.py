from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "faq"


def _company_dir(company_id: str) -> Path:
    d = DATA_DIR / company_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _file(company_id: str, name: str) -> Path:
    return _company_dir(company_id) / name


def load_faq(company_id: str) -> list[dict]:
    path = _file(company_id, "faq.json")
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save_faq(company_id: str, items: list[dict]):
    path = _file(company_id, "faq.json")
    path.write_text(json.dumps(items, indent=2))


def load_candidates(company_id: str) -> list[dict]:
    path = _file(company_id, "candidates.json")
    if not path.exists():
        return []
    return json.loads(path.read_text())


def save_candidates(company_id: str, items: list[dict]):
    path = _file(company_id, "candidates.json")
    path.write_text(json.dumps(items, indent=2))
