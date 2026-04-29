from __future__ import annotations

import base64
import os
import tempfile
import time
from typing import Tuple

from openai import OpenAI


def stt_from_base64(audio_base64: str, language_hint: str | None = "pt") -> Tuple[str, float, str]:
    started = time.perf_counter()

    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except Exception:
        return "", round(time.perf_counter() - started, 3), "invalid_base64"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "", round(time.perf_counter() - started, 3), "openai_missing_key"

    suffix = ".wav"

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as audio_file:
            audio_file.write(audio_bytes)
            audio_file.flush()

            client = OpenAI(api_key=api_key)

            with open(audio_file.name, "rb") as file:
                result = client.audio.transcriptions.create(
                    model=os.getenv("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe"),
                    file=file,
                    language=language_hint or "pt",
                )

        text = (getattr(result, "text", None) or "").strip()
        return text, round(time.perf_counter() - started, 3), "openai"

    except Exception as exc:
        return "", round(time.perf_counter() - started, 3), f"openai_error:{type(exc).__name__}"
