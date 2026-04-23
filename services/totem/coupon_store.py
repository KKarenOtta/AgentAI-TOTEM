from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from services.totem.metrics import MetricsLogger
from services.totem.qr import generate_qr_from_text


COUPONS_PATH = "data/coupons/coupons.jsonl"
metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")


def _ensure_storage() -> None:
    os.makedirs("data/coupons", exist_ok=True)
    if not os.path.exists(COUPONS_PATH):
        with open(COUPONS_PATH, "w", encoding="utf-8"):
            pass


def _read_all() -> list[dict[str, Any]]:
    _ensure_storage()

    rows: list[dict[str, Any]] = []
    with open(COUPONS_PATH, "r", encoding="utf-8") as file:
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
    with open(COUPONS_PATH, "w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_cpf(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    return digits or None


def _get_public_base_url() -> str:
    base_url = (
        os.getenv("TOTEM_PUBLIC_BASE_URL")
        or os.getenv("APP_BASE_URL")
        or "http://127.0.0.1:8000"
    ).strip()
    return base_url.rstrip("/")


def _get_expiration_days() -> int:
    try:
        return max(1, int(os.getenv("COUPON_EXPIRATION_DAYS", "7")))
    except Exception:
        return 7


def _now() -> datetime:
    return datetime.now()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _refresh_coupon_status(coupon: dict[str, Any]) -> dict[str, Any]:
    if coupon.get("status") == "redeemed":
        return coupon

    expires_at = _parse_dt(coupon.get("expires_at"))
    if expires_at and _now() > expires_at:
        coupon["status"] = "expired"

    return coupon


def _refresh_all_statuses(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changed = False
    for row in rows:
        before = row.get("status")
        _refresh_coupon_status(row)
        if row.get("status") != before:
            changed = True

    if changed:
        _write_all(rows)

    return rows


def list_coupons_by_lead(lead_id: str) -> list[dict[str, Any]]:
    rows = _refresh_all_statuses(_read_all())
    return [row for row in rows if row.get("lead_id") == lead_id]


def get_coupon_by_id(coupon_id: str) -> dict[str, Any] | None:
    rows = _refresh_all_statuses(_read_all())
    for row in rows:
        if row.get("coupon_id") == coupon_id:
            return row
    return None


def _find_existing_coupon(
    rows: list[dict[str, Any]],
    company_id: str,
    campaign_id: str,
    lead_id: str,
    email: str,
    cpf: str | None,
) -> dict[str, Any] | None:
    for row in rows:
        if row.get("company_id") != company_id:
            continue
        if row.get("campaign_id") != campaign_id:
            continue

        same_lead = row.get("lead_id") == lead_id
        same_email = _normalize_email(row.get("email")) == email
        same_cpf = cpf and _normalize_cpf(row.get("cpf")) == cpf

        if not (same_lead or same_email or same_cpf):
            continue

        _refresh_coupon_status(row)

        if row.get("status") in {"available", "redeemed", "expired"}:
            return row

    return None


def create_coupon(lead: dict[str, Any], campaign: dict[str, Any]) -> dict[str, Any] | None:
    _ensure_storage()

    company_id = lead.get("company_id")
    campaign_id = campaign.get("campaign_id")
    lead_id = lead.get("lead_id")
    email = _normalize_email(lead.get("email"))
    cpf = _normalize_cpf(lead.get("cpf"))

    if not company_id or not campaign_id or not lead_id:
        return None

    rows = _refresh_all_statuses(_read_all())

    existing = _find_existing_coupon(
        rows=rows,
        company_id=company_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        email=email,
        cpf=cpf,
    )
    if existing:
        return existing

    coupon_id = uuid4().hex
    expires_at = (_now() + timedelta(days=_get_expiration_days())).isoformat(timespec="seconds")
    redeem_url = f"{_get_public_base_url()}/store/redeem?coupon_id={coupon_id}"
    qr_url = generate_qr_from_text(redeem_url)

    coupon = {
        "coupon_id": coupon_id,
        "company_id": company_id,
        "lead_id": lead_id,
        "email": email,
        "cpf": cpf,
        "campaign_id": campaign_id,
        "title": campaign.get("title") or campaign.get("name") or "Campanha",
        "description": campaign.get("description") or "",
        "media_image": campaign.get("media_image") or "",
        "code": campaign.get("coupon_code") or "",
        "discount_type": campaign.get("discount_type") or "",
        "discount_value": campaign.get("discount_value") or 0,
        "cta_label": campaign.get("cta_label") or "Use na loja",
        "status": "available",
        "issued_at": _now().isoformat(timespec="seconds"),
        "expires_at": expires_at,
        "redeemed_at": None,
        "store_id": None,
        "operator_id": None,
        "validation_message": "Cupom disponível para uso.",
        "redeem_url": redeem_url,
        "qr_url": qr_url,
    }

    with open(COUPONS_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(coupon, ensure_ascii=False) + "\n")

    try:
        metrics_logger.save(
            {
                "event": "coupon_issued",
                "timestamp": coupon["issued_at"],
                "company_id": company_id,
                "lead_id": lead_id,
                "email": email,
                "cpf": cpf,
                "campaign_id": campaign_id,
                "coupon_id": coupon_id,
                "coupon_code": coupon["code"],
                "discount_type": coupon["discount_type"],
                "discount_value": coupon["discount_value"],
                "status": coupon["status"],
                "expires_at": expires_at,
            }
        )
    except Exception:
        pass

    return coupon


def redeem_coupon(
    coupon_id: str,
    store_id: str | None = None,
    operator_id: str | None = None,
) -> dict[str, Any] | None:
    rows = _read_all()
    rows = _refresh_all_statuses(rows)

    found: dict[str, Any] | None = None
    changed = False

    for row in rows:
        if row.get("coupon_id") != coupon_id:
            continue

        _refresh_coupon_status(row)

        if row.get("status") == "expired":
            row["validation_message"] = "Cupom expirado."
            found = row
            break

        if row.get("status") == "redeemed":
            row["validation_message"] = "Cupom já resgatado anteriormente."
            found = row
            break

        row["status"] = "redeemed"
        row["redeemed_at"] = _now().isoformat(timespec="seconds")
        row["store_id"] = (store_id or "").strip() or None
        row["operator_id"] = (operator_id or "").strip() or None
        row["validation_message"] = "Cupom validado com sucesso."
        found = row
        changed = True
        break

    if found is None:
        return None

    if changed:
        _write_all(rows)

        try:
            metrics_logger.save(
                {
                    "event": "coupon_redeemed",
                    "timestamp": found["redeemed_at"],
                    "company_id": found.get("company_id"),
                    "lead_id": found.get("lead_id"),
                    "email": found.get("email"),
                    "cpf": found.get("cpf"),
                    "campaign_id": found.get("campaign_id"),
                    "coupon_id": found.get("coupon_id"),
                    "coupon_code": found.get("code"),
                    "discount_type": found.get("discount_type"),
                    "discount_value": found.get("discount_value"),
                    "status": found.get("status"),
                    "store_id": found.get("store_id"),
                    "operator_id": found.get("operator_id"),
                }
            )
        except Exception:
            pass

    return found
