from __future__ import annotations

import os
import subprocess
from pathlib import Path

AUDIO_PATH = Path("/tmp/input.wav")
ARECORD_DEVICE = os.getenv("ARECORD_DEVICE", "plughw:2,0")
ARECORD_FORMAT = os.getenv("ARECORD_FORMAT", "cd")


def record_audio(seconds: int = 4) -> str | None:
    print("[AUDIO] gravando...")

    if AUDIO_PATH.exists():
        AUDIO_PATH.unlink()

    cmd = [
        "arecord",
        "-D",
        ARECORD_DEVICE,
        "-f",
        ARECORD_FORMAT,
        "-d",
        str(seconds),
        str(AUDIO_PATH),
    ]

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("[ERRO] arecord não está instalado")
        return None
    except Exception as exc:
        print(f"[ERRO] falha ao iniciar gravação: {exc}")
        return None

    if result.returncode != 0:
        print("[ERRO] falha ao gravar áudio")
        if result.stderr:
            print(result.stderr.strip())
        return None

    if not AUDIO_PATH.exists() or AUDIO_PATH.stat().st_size == 0:
        print("[ERRO] arquivo de áudio não foi criado corretamente")
        return None

    print("[AUDIO] gravação concluída")
    return str(AUDIO_PATH)
