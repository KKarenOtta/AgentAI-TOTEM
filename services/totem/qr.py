from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import qrcode


QR_DIR = Path("static/uploads/qrcodes")
QR_DIR.mkdir(parents=True, exist_ok=True)


def generate_campaign_qr(payload: dict) -> str:
    filename = f"{uuid4().hex}.png"
    out_path = QR_DIR / filename

    img = qrcode.make(json.dumps(payload, ensure_ascii=False))
    img.save(out_path)

    return f"/static/uploads/qrcodes/{filename}"
