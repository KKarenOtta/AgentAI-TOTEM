from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

TOTEM_API_URL = os.getenv("TOTEM_API_URL", "").strip()
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001").strip()
DEVICE_ID = os.getenv("DEVICE_ID", "RPI3-PRESENCE-001").strip()

ULTRASONIC_SENSORS = [
    {
        "name": "Esquerda",
        "trig": int(os.getenv("ULTRA_LEFT_TRIG", "17")),
        "echo": int(os.getenv("ULTRA_LEFT_ECHO", "27")),
    },
    {
        "name": "Centro",
        "trig": int(os.getenv("ULTRA_CENTER_TRIG", "22")),
        "echo": int(os.getenv("ULTRA_CENTER_ECHO", "23")),
    },
    {
        "name": "Direita",
        "trig": int(os.getenv("ULTRA_RIGHT_TRIG", "24")),
        "echo": int(os.getenv("ULTRA_RIGHT_ECHO", "25")),
    },
]

DISTANCE_TRIGGER_CM = float(os.getenv("DISTANCE_TRIGGER_CM", "100"))
MIN_APPROACH_DROP_CM = float(os.getenv("MIN_APPROACH_DROP_CM", "15"))
PRESENCE_HOLD_SECONDS = float(os.getenv("PRESENCE_HOLD_SECONDS", "3"))
SAMPLE_INTERVAL_SECONDS = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "0.25"))
MIN_ACTIVE_RATIO = float(os.getenv("MIN_ACTIVE_RATIO", "0.45"))

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_WARMUP_SECONDS = float(os.getenv("CAMERA_WARMUP_SECONDS", "1.0"))
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "1280"))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "720"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "85"))

REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "10"))
WARMUP_SECONDS = float(os.getenv("WARMUP_SECONDS", "3"))
