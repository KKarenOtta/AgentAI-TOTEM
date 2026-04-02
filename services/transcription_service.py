from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

OPENAI_MODEL = "whisper-1"
AUDIO_TRANSCRIBE_PROVIDER = os.getenv("AUDIO_TRANSCRIBE_PROVIDER", "auto").strip().lower()
AUDIO_TRANSCRIBE_LANGUAGE = os.getenv("AUDIO_TRANSCRIBE_LANGUAGE", "pt").strip().lower()

WHISPER_CPP_BIN = os.getenv("WHISPER_CPP_BIN", "").strip()
WHISPER_CPP_MODEL = os.getenv("WHISPER_CPP_MODEL", "").strip()

_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client

    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada")
        _openai_client = OpenAI(api_key=api_key)

    return _openai_client


def transcribe_with_openai(audio_path: str | Path) -> dict:
    client = _get_openai_client()
    audio_path = str(audio_path)

    with open(audio_path, "rb") as audio_handle:
        transcript = client.audio.transcriptions.create(
            model=OPENAI_MODEL,
            file=audio_handle,
            language=AUDIO_TRANSCRIBE_LANGUAGE,
        )

    text = (getattr(transcript, "text", "") or "").strip()
    if not text:
        raise RuntimeError("A OpenAI retornou transcrição vazia")

    return {
        "text": text,
        "provider": "openai",
        "model": OPENAI_MODEL,
        "fallback_used": False,
    }


def transcribe_with_whisper_cpp(audio_path: str | Path) -> dict:
    if not WHISPER_CPP_BIN:
        raise RuntimeError("WHISPER_CPP_BIN não configurado")

    if not WHISPER_CPP_MODEL:
        raise RuntimeError("WHISPER_CPP_MODEL não configurado")

    audio_path = str(audio_path)

    with tempfile.TemporaryDirectory(prefix="whispercpp_") as tmpdir:
        out_prefix = str(Path(tmpdir) / "result")

        cmd = [
            WHISPER_CPP_BIN,
            "-m", WHISPER_CPP_MODEL,
            "-f", audio_path,
            "-l", AUDIO_TRANSCRIBE_LANGUAGE,
            "-otxt",
            "-of", out_prefix,
            "-np",
        ]

        print(f"[AUDIO] executando fallback local: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            details = stderr or stdout or "falha sem saída"
            raise RuntimeError(f"whisper.cpp falhou: {details}")

        txt_file = Path(out_prefix + ".txt")
        if not txt_file.exists():
            raise RuntimeError("whisper.cpp não gerou arquivo de saída")

        text = txt_file.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError("whisper.cpp retornou transcrição vazia")

        return {
            "text": text,
            "provider": "local",
            "model": Path(WHISPER_CPP_MODEL).name,
            "fallback_used": True,
        }


def transcribe_audio(audio_path: str | Path) -> dict:
    provider = AUDIO_TRANSCRIBE_PROVIDER

    if provider == "openai":
        return transcribe_with_openai(audio_path)

    if provider == "local":
        return transcribe_with_whisper_cpp(audio_path)

    openai_error: str | None = None

    try:
        return transcribe_with_openai(audio_path)
    except Exception as exc:
        openai_error = str(exc)
        print(f"[AUDIO] OpenAI indisponível: {openai_error}")

    local_result = transcribe_with_whisper_cpp(audio_path)
    local_result["openai_error"] = openai_error
    return local_result
