from __future__ import annotations

import base64
import os
import time
from pathlib import Path

from openai import OpenAI

from core.totem.stt import stt_from_base64
from core.totem.tts import gerar_audio


BASE_DIR = Path(__file__).resolve().parents[2]
PUBLIC_AUDIO_DIR = BASE_DIR / "static" / "audio"
PUBLIC_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_AUDIO_FILE = PUBLIC_AUDIO_DIR / "resposta.mp3"


def _build_public_audio_result(audio_path: str | None) -> tuple[str | None, str | None]:
    """
    Se o TTS ja salvou no arquivo publico, apenas devolve o path/url.
    Nao copia nada.
    """
    if not audio_path:
        return None, None

    path_obj = Path(audio_path)

    if not path_obj.exists():
        return None, None

    cache_buster = int(time.time())
    return str(path_obj), f"/static/audio/resposta.mp3?t={cache_buster}"


def _generate_answer_text(transcript: str) -> tuple[str, str]:
    transcript = (transcript or "").strip()

    if not transcript:
        return "Nao entendi o que foi dito.", "empty_transcript"

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini").strip()

    if not api_key:
        return f"Recebi sua mensagem: {transcript}", "fallback_no_key"

    try:
        client = OpenAI(api_key=api_key)

        response = client.responses.create(
            model=model,
            input=(
                "Responda em portugues do Brasil, de forma curta, clara e objetiva, "
                f"para um totem interativo. Pergunta do visitante: {transcript}"
            ),
        )

        answer_text = (getattr(response, "output_text", None) or "").strip()

        if not answer_text:
            return f"Recebi sua mensagem: {transcript}", "fallback_empty_response"

        return answer_text, "openai"

    except Exception as exc:
        return f"Recebi sua mensagem: {transcript}", f"fallback_error:{type(exc).__name__}"


def process_interaction(
    company_id: str,
    session_id: str,
    message: str = "",
    audio_bytes: bytes | None = None,
):
    transcript = (message or "").strip()
    stt_latency = 0
    stt_source = "text"

    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        transcript, stt_latency, stt_source = stt_from_base64(audio_b64)

    answer_text, llm_source = _generate_answer_text(transcript)

    raw_audio_path, tts_source, tts_status, tts_error, tts_latency = gerar_audio(answer_text)
    public_audio_path, public_audio_url = _build_public_audio_result(raw_audio_path)

    return {
        "company_id": company_id,
        "session_id": session_id,
        "transcript": transcript,
        "answer_text": answer_text,
        "audio_path": public_audio_path,
        "audio_url": public_audio_url,
        "language": "pt-BR",
        "stt_source": stt_source,
        "stt_latency": stt_latency,
        "llm_source": llm_source,
        "tts_source": tts_source,
        "tts_status": tts_status,
        "tts_error": tts_error,
        "tts_latency": tts_latency,
    }
