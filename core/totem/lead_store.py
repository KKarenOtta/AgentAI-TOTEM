from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from core.totem.consent_store import save_consent
from core.totem.metrics import MetricsLogger
from core.totem.qr import generate_qr_from_text
from core.totem.recovery_store import save_recovery_memory

LEADS_PATH = "data/leads/leads.jsonl"
metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")


def _ensure_storage() -> None:
    os.makedirs("data/leads", exist_ok=True)

    if not os.path.exists(LEADS_PATH):
        with open(LEADS_PATH, "w", encoding="utf-8"):
            pass


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_cpf(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    return digits or None


def _normalize_favorite_brands(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    return []


def _get_public_base_url() -> str:
    base_url = (
        os.getenv("TOTEM_PUBLIC_BASE_URL")
        or os.getenv("APP_BASE_URL")
        or "http://127.0.0.1:8000"
    ).strip()

    return base_url.rstrip("/")


def _read_all() -> list[dict[str, Any]]:
    _ensure_storage()

    rows: list[dict[str, Any]] = []

    with open(LEADS_PATH, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return rows


def _write_all(rows: list[dict[str, Any]]) -> None:
    _ensure_storage()

    with open(LEADS_PATH, "w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def get_lead_by_id(lead_id: str) -> dict[str, Any] | None:
    for row in reversed(_read_all()):
        if row.get("lead_id") == lead_id:
            return row

    return None


def find_existing_lead(company_id: str, session_id: str, email: str | None, cpf: str | None = None) -> dict[str, Any] | None:
    email = _normalize_email(email)
    cpf = _normalize_cpf(cpf)

    for row in reversed(_read_all()):
        if row.get("company_id") != company_id:
            continue

        same_session = row.get("session_id") == session_id
        same_email = email and _normalize_email(row.get("email")) == email
        same_cpf = cpf and _normalize_cpf(row.get("cpf")) == cpf

        if same_session or same_email or same_cpf:
            return row

    return None


def save_lead(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_storage()

    company_id = (payload.get("company_id") or "").strip()
    session_id = (payload.get("session_id") or "").strip()
    email = _normalize_email(payload.get("email"))
    cpf = _normalize_cpf(payload.get("cpf"))

    if not company_id:
        raise ValueError("company_id é obrigatório.")

    if not session_id:
        raise ValueError("session_id é obrigatório.")

    if not email:
        raise ValueError("email é obrigatório.")

    rows = _read_all()
    existing = find_existing_lead(company_id, session_id, email, cpf)

    now = datetime.now().isoformat(timespec="seconds")

    if existing:
        lead = dict(existing)
        lead["updated_at"] = now
    else:
        lead = {
            "lead_id": uuid4().hex,
            "timestamp": now,
            "created_at": now,
        }

    lead.update(
        {
            "company_id": company_id,
            "session_id": session_id,
            "full_name": (payload.get("full_name") or "").strip(),
            "email": email,
            "cpf": cpf or "",
            "phone": (payload.get("phone") or "").strip(),
            "age": int(payload.get("age") or 0),
            "gender": str(payload.get("gender") or "unknown").strip(),
            "favorite_brands": _normalize_favorite_brands(payload.get("favorite_brands")),
            "lgpd_consent": bool(payload.get("lgpd_consent")),
            "newsletter_opt_in": bool(payload.get("newsletter_opt_in", True)),
            "consent_version": payload.get("consent_version") or "lgpd-v1",
            "source": payload.get("source") or "device",
            "ip_address": payload.get("ip_address"),
            "user_agent": payload.get("user_agent"),
        }
    )

    new_rows = [row for row in rows if row.get("lead_id") != lead["lead_id"]]
    new_rows.append(lead)
    _write_all(new_rows)

    save_consent(
        {
            "company_id": lead["company_id"],
            "session_id": lead["session_id"],
            "lead_id": lead["lead_id"],
            "email": lead["email"],
            "full_name": lead["full_name"],
            "lgpd_consent": lead["lgpd_consent"],
            "newsletter_opt_in": lead["newsletter_opt_in"],
            "consent_version": lead["consent_version"],
            "consent_text": payload.get("consent_text") or "",
            "source": lead["source"],
            "ip_address": lead["ip_address"],
            "user_agent": lead["user_agent"],
        }
    )

    recovery = save_recovery_memory(
        {
            "company_id": lead["company_id"],
            "session_id": lead["session_id"],
            "lead_id": lead["lead_id"],
            "email": lead["email"],
            "research_summary": payload.get("research_summary") or "",
            "recommendations_snapshot": payload.get("recommendations_snapshot") or {},
            "source": lead["source"],
        }
    )

    public_base_url = _get_public_base_url()
    access_page_url = f"{public_base_url}/lead/access/{lead['lead_id']}"
    recovery_page_url = f"{public_base_url}/recovery/{recovery['memory_id']}"

    lead["access_page_url"] = access_page_url
    lead["recovery_page_url"] = recovery_page_url
    lead["access_qr_url"] = generate_qr_from_text(access_page_url)
    lead["recovery_qr_url"] = generate_qr_from_text(recovery_page_url)

    new_rows = [row for row in _read_all() if row.get("lead_id") != lead["lead_id"]]
    new_rows.append(lead)
    _write_all(new_rows)

    try:
        metrics_logger.save(
            {
                "event": "lead_capture",
                "timestamp": now,
                "company_id": lead["company_id"],
                "session_id": lead["session_id"],
                "lead_id": lead["lead_id"],
                "email": lead["email"],
                "cpf": lead["cpf"],
                "gender": lead["gender"],
                "age": lead["age"],
                "lgpd_consent": lead["lgpd_consent"],
                "newsletter_opt_in": lead["newsletter_opt_in"],
                "source": lead["source"],
                "access_qr_url": lead["access_qr_url"],
                "recovery_qr_url": lead["recovery_qr_url"],
                "access_page_url": access_page_url,
                "recovery_page_url": recovery_page_url,
            }
        )
    except Exception:
        pass

    return lead
