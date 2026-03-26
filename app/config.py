from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AgentAI-TOTEM")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "9000"))
    default_company_id: str = os.getenv("DEFAULT_COMPANY_ID", "FLX-001")
    presence_timeout_s: int = int(os.getenv("PRESENCE_TIMEOUT_S", "15"))


settings = Settings()
