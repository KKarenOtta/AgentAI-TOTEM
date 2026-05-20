from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import qrcode


QR_DIR = Path("static/uploads/qrcodes")
QR_DIR.mkdir(parents=True, exist_ok=True)


def _public_base_url() -> str:
    return os.getenv("TOTEM_PUBLIC_BASE_URL", "http://52.201.76.45:8000").rstrip("/")


def _save_qr_content(content: str) -> str:
    filename = f"{uuid4().hex}.png"
    out_path = QR_DIR / filename

    img = qrcode.make(content)
    img.save(out_path)

    return f"{_public_base_url()}/static/uploads/qrcodes/{filename}"


def generate_qr_from_text(content: str) -> str:
    return _save_qr_content(content)


def generate_campaign_qr(payload: dict) -> str:
    return _save_qr_content(json.dumps(payload, ensure_ascii=False))
