import os

APP_ROLE = os.getenv("APP_ROLE", "edge").strip().lower()

IS_EDGE = APP_ROLE == "edge"
IS_CLOUD = APP_ROLE == "cloud"

CLOUD_BASE_URL = os.getenv("CLOUD_BASE_URL", "").rstrip("/")
EDGE_PUSH_MODE = os.getenv("EDGE_PUSH_MODE", "websocket").strip().lower()

STT_MODE = os.getenv("STT_MODE", "remote").strip().lower()
TTS_MODE = os.getenv("TTS_MODE", "remote").strip().lower()
ML_MODE = os.getenv("ML_MODE", "remote").strip().lower()
