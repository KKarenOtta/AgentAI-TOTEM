from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import qrcode


QR_DIR = Path("static/uploads/qrcodes")
QR_DIR.mkdir(parents=True, exist_ok=True)


def _save_qr_content(content: str) -> str:
    filename = f"{uuid4().hex}.png"
    out_path = QR_DIR / filename

    img = qrcode.make(content)
    img.save(out_path)

    return f"/static/uploads/qrcodes/{filename}"


def generate_qr_from_text(content: str) -> str:
    return _save_qr_content(content)


def generate_campaign_qr(payload: dict) -> str:
    return _save_qr_content(json.dumps(payload, ensure_ascii=False))
