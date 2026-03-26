from __future__ import annotations

import os


API_BASE_URL = os.getenv("TOTEM_API_URL", "http://127.0.0.1:9000/api").rstrip("/")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001")
DEVICE_ID = os.getenv("DEVICE_ID", "RPI3-PIR-001")
PIR_PIN = int(os.getenv("PIR_PIN", "17"))
POLL_INTERVAL_S = float(os.getenv("POLL_INTERVAL_S", "0.20"))
CLEAR_DELAY_S = float(os.getenv("CLEAR_DELAY_S", "4"))
