from __future__ import annotations

import base64
import os
import tempfile
import time
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", override=True)
print("=== STT MODULE CARREGADO ===", __file__, flush=True)

def stt_from_base64(audio_base64: str, language_hint: str | None = "pt") -> Tuple[str, float, str]:
    started = time.perf_counter()
    print("=== STT: entrou em stt_from_base64 ===", flush=True)
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except Exception:
        return "", round(time.perf_counter() - started, 3), "invalid_base64"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe").strip()

    if not api_key:
        return "", round(time.perf_counter() - started, 3), "openai_missing_key"

    try:
        client = OpenAI(api_key=api_key)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as audio_file:
            audio_file.write(audio_bytes)
            audio_file.flush()

            with open(audio_file.name, "rb") as file:
                result = client.audio.transcriptions.create(
                    model=model,
                    file=file,
                    language=language_hint or "pt",
                )

        text = (getattr(result, "text", None) or "").strip()
        return text, round(time.perf_counter() - started, 3), "openai"

    except Exception as exc:
        return "", round(time.perf_counter() - started, 3), f"openai_error:{type(exc).__name__}"

sttfrombase64 = stt_from_base64
