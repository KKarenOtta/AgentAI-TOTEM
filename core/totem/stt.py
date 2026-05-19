from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env", override=True)
<<<<<<< HEAD
print("=== STT MODULE CARREGADO ===", __file__, flush=True)

def stt_from_base64(audio_base64: str, language_hint: str | None = "pt") -> Tuple[str, float, str]:
    started = time.perf_counter()
    print("=== STT: entrou em stt_from_base64 ===", flush=True)
=======

print("=== CARREGOU core/totem/stt.py ===", __file__, flush=True)

def stt_from_base64(audio_base64: str, language_hint: str | None = "pt") -> Tuple[str, float, str]:
    started = time.perf_counter()
    print("=== ENTROU stt_from_base64 ===", flush=True)
    
>>>>>>> 3fcc2d5083f40a520be268d70f73cb00bb2d7457
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except Exception as exc:
        return "", round(time.perf_counter() - started, 3), f"invalid_base64:{type(exc).__name__}:{str(exc)}"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe").strip()

    if not api_key:
        return "", round(time.perf_counter() - started, 3), "openai_missing_key"

    try:
        client = OpenAI(api_key=api_key)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as audio_file:
            audio_file.write(audio_bytes)
            audio_file.flush()

            print({
                "stt_debug": {
                    "model": model,
                    "language": language_hint or "pt",
                    "tmp_file": audio_file.name,
                    "audio_bytes": len(audio_bytes),
                }
            }, flush=True)

            with open(audio_file.name, "rb") as file:
                result = client.audio.transcriptions.create(
                    model=model,
                    file=file,
                    language=language_hint or "pt",
                    response_format="verbose_json",
                )

        text = (getattr(result, "text", None) or "").strip()
        language = getattr(result, "language", None)
        duration = getattr(result, "duration", None)

        print({
            "stt_result": {
                "text": text,
                "language": language,
                "duration": duration,
                "result_repr": str(result),
            }
        }, flush=True)

        if not text:
            return "", round(time.perf_counter() - started, 3), f"openai_empty_text:language={language}:duration={duration}"

        return text, round(time.perf_counter() - started, 3), f"openai:{model}"

    except Exception as exc:
<<<<<<< HEAD
        return "", round(time.perf_counter() - started, 3), f"openai_error:{type(exc).__name__}"
=======
        print({
            "stt_error": {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        }, flush=True)
        return "", round(time.perf_counter() - started, 3), f"openai_error:{type(exc).__name__}:{str(exc)}"    
>>>>>>> 3fcc2d5083f40a520be268d70f73cb00bb2d7457

sttfrombase64 = stt_from_base64
