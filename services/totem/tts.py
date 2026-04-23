from __future__ import annotations

import os
import time
from pathlib import Path

import requests
from gtts import gTTS


AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def _language_code_for_elevenlabs(idioma: str) -> str | None:
    mapping = {
        "pt": "pt",
        "en": "en",
        "es": "es",
    }
    return mapping.get(idioma)


def _save_bytes(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)


def gerar_audio(
    texto: str,
    idioma: str = "pt",
    hugging_key: str | None = None,
):
    texto = (texto or "").strip()
    if not texto:
        return None, "none", None, "texto_vazio", 0.0

    eleven_api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    eleven_voice_id = (
        os.getenv("ELEVENLABS_VOICE_ID")
        or os.getenv("ELEVENLABS_VOICE_ID_PT")
        or ""
    ).strip()
    eleven_model_id = (
        os.getenv("ELEVENLABS_MODEL_ID")
        or "eleven_flash_v2_5"
    ).strip()

    if eleven_api_key and eleven_voice_id:
        try:
            api_url = (
                f"https://api.elevenlabs.io/v1/text-to-speech/"
                f"{eleven_voice_id}?output_format=mp3_44100_128"
            )

            payload = {
                "text": texto,
                "model_id": eleven_model_id,
                "voice_settings": {
                    "stability": 0.45,
                    "similarity_boost": 0.8,
                },
            }

            language_code = _language_code_for_elevenlabs(idioma)
            if language_code:
                payload["language_code"] = language_code

            headers = {
                "xi-api-key": eleven_api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }

            t0 = time.perf_counter()
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            t1 = time.perf_counter()

            latency = round(t1 - t0, 3)

            if response.status_code == 200 and response.content:
                out_path = AUDIO_DIR / "voz_elevenlabs.mp3"
                saved = _save_bytes(out_path, response.content)
                return saved, "elevenlabs", response.status_code, None, latency

            err_text = (response.text or "")[:800]
            # continua para fallback
            fallback_error = f"elevenlabs_http_{response.status_code}: {err_text}"

        except Exception as exc:
            fallback_error = f"elevenlabs_exception: {exc}"
    else:
        fallback_error = "elevenlabs_nao_configurado"

    try:
        t0 = time.perf_counter()
        lang_map = {"pt": "pt", "en": "en", "es": "es"}
        lang_final = lang_map.get(idioma, "pt")

        tts = gTTS(text=texto, lang=lang_final)
        out_path = AUDIO_DIR / "voz_fallback.mp3"
        tts.save(str(out_path))

        t1 = time.perf_counter()
        latency = round(t1 - t0, 3)

        return str(out_path), "gTTS", None, fallback_error, latency
    except Exception as exc:
        return None, "error", None, f"{fallback_error} | gtts_exception: {exc}", 0.0
