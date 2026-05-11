from __future__ import annotations

import json
from pathlib import Path

from core.auth.password import hash_password, is_legacy_hash, verify_password

USERS_FILE = Path("data/users.json")


def _ensure_file() -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]\n", encoding="utf-8")


def load_users() -> list[dict]:
    _ensure_file()

    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_users(users: list[dict]) -> None:
    _ensure_file()
    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def public_users() -> list[dict]:
    safe = []

    for user in load_users():
        item = dict(user)
        item.pop("password", None)
        item["has_password"] = bool(user.get("password"))
        safe.append(item)

    return safe


def find_user(username: str) -> dict | None:
    username = username.strip()
    return next((user for user in load_users() if user.get("username") == username), None)


def authenticate(username: str, password: str) -> dict | None:
    username = username.strip()
    user = find_user(username)

    if not user:
        return None

    stored_hash = user.get("password", "")

    if not verify_password(password, stored_hash):
        return None

    if is_legacy_hash(stored_hash):
        _upgrade_password_hash(username, password)

    safe_user = dict(user)
    safe_user.pop("password", None)

    return safe_user


def upsert_company_user(username: str, password: str, company_id: str) -> dict:
    username = username.strip()
    company_id = company_id.strip()

    if not username:
        raise ValueError("username obrigatório")

    if not password:
        raise ValueError("password obrigatório")

    if not company_id:
        raise ValueError("company_id obrigatório")

    users = load_users()

    payload = {
        "username": username,
        "password": hash_password(password),
        "role": "company",
        "company_id": company_id,
    }

    for index, user in enumerate(users):
        if user.get("username") == username:
            users[index] = payload
            save_users(users)
            return dict(payload, password="<HASH_OCULTO>")

    users.append(payload)
    save_users(users)

    return dict(payload, password="<HASH_OCULTO>")


def delete_user(username: str) -> bool:
    username = username.strip()

    users = load_users()
    kept = []
    removed = False

    for user in users:
        if user.get("username") == username:
            if user.get("role") == "admin":
                kept.append(user)
                continue

            removed = True
            continue

        kept.append(user)

    save_users(kept)
    return removed


def _upgrade_password_hash(username: str, password: str) -> None:
    users = load_users()

    for user in users:
        if user.get("username") == username:
            user["password"] = hash_password(password)
            break

    save_users(users)
