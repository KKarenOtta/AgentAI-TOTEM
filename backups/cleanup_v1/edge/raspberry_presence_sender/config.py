import os
from dotenv import load_dotenv

load_dotenv()

# API / identidade
TOTEM_API_URL = os.getenv("TOTEM_API_URL", "").strip()
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001").strip()
DEVICE_ID = os.getenv("DEVICE_ID", "RPI3-PRESENCE-001").strip()

# PIR
PIR_PIN = int(os.getenv("PIR_PIN", "17"))
PRESENCE_HOLD_SECONDS = float(os.getenv("PRESENCE_HOLD_SECONDS", "5"))

# câmera
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
CAMERA_WARMUP_SECONDS = float(os.getenv("CAMERA_WARMUP_SECONDS", "1.0"))
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", "480"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "85"))

# rede
REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "10"))
