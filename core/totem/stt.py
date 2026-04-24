import base64
import os
import time
from typing import Tuple

def stt_from_base64(audio_base64: str, language_hint: str | None = None) -> Tuple[str, float, str]:
    """
    Retorna (text, latency_s, provider).
    Provider pode ser "demo" por enquanto.
    """
    t0 = time.perf_counter()

    # valida base64
    try:
        _ = base64.b64decode(audio_base64, validate=True)
    except Exception:
        t1 = time.perf_counter()
        return ("[STT_DEMO] Áudio inválido (base64).", round(t1 - t0, 3), "demo")

    # TODO: plugar STT real (OpenAI / Whisper local / HF)
    # Por enquanto: fallback de desenvolvimento
    t1 = time.perf_counter()
    return ("[STT_DEMO] (texto reconhecido do áudio) Quais promoções estão ativas para mim hoje?",
            round(t1 - t0, 3),
            "demo")