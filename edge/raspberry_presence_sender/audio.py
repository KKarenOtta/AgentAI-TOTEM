import subprocess
import time
import os

AUDIO_PATH = "/tmp/input.wav"


def record_audio(seconds=4) -> str | None:
    print("[AUDIO] gravando...")

    if os.path.exists(AUDIO_PATH):
        os.remove(AUDIO_PATH)

    cmd = [
        "arecord",
        "-D", "plughw:2,0",
        "-f", "cd",
        "-d", str(seconds),
        AUDIO_PATH
    ]

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("[ERRO] falha ao gravar áudio")
        return None

    if not os.path.exists(AUDIO_PATH):
        print("[ERRO] arquivo não criado")
        return None

    print("[AUDIO] gravação concluída")
    return AUDIO_PATH
