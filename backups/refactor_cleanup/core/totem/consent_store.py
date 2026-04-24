from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any
from uuid import uuid4


CONSENTS_PATH = "data/lgpd/consents.jsonl"


def save_consent(payload: dict[str, Any]) -> dict[str, Any]:
    os.makedirs("data/lgpd", exist_ok=True)

    consent = {
        "consent_id": uuid4().hex,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "company_id": payload["company_id"],
        "session_id": payload["session_id"],
        "lead_id": payload["lead_id"],
        "email": payload["email"].strip().lower(),
        "full_name": payload["full_name"].strip(),
        "lgpd_consent": bool(payload["lgpd_consent"]),
        "newsletter_opt_in": bool(payload.get("newsletter_opt_in", True)),
        "consent_version": payload.get("consent_version") or "lgpd-v1",
        "consent_text": payload.get("consent_text") or "",
        "source": payload.get("source") or "totem_live",
        "ip_address": payload.get("ip_address"),
        "user_agent": payload.get("user_agent"),
    }

    with open(CONSENTS_PATH, "a", encoding="utf-8") as file:
        file.write(json.dumps(consent, ensure_ascii=False) + "\n")

    return consent
