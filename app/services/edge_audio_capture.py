from __future__ import annotations

import os
import subprocess
from pathlib import Path

RECORDINGS_DIR = Path("data/recordings")
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


def record_question(session_id: str) -> str:
    duration = os.getenv("EDGE_AUDIO_DURATION", "5").strip()
    device = os.getenv("EDGE_AUDIO_DEVICE", "default").strip()
    sample_rate = os.getenv("EDGE_AUDIO_RATE", "16000").strip()
    channels = os.getenv("EDGE_AUDIO_CHANNELS", "1").strip()

    out = RECORDINGS_DIR / f"{session_id}.wav"

    cmd = [
        "arecord",
        "-D", device,
        "-d", duration,
        "-f", "S16_LE",
        "-r", sample_rate,
        "-c", channels,
        "-t", "wav",
        str(out),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RuntimeError(f"Falha ao gravar audio com arecord. stdout={stdout} stderr={stderr}")

    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("Arquivo de audio nao foi gerado corretamente.")

    return str(out)
