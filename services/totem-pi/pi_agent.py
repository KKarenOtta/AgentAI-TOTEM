import base64
import time
import json
import requests
import sounddevice as sd
import numpy as np
from gpiozero import MotionSensor

TOTEM_BASE_URL = "http://192.168.0.10:9000"  # <-- troque para o IP do seu servidor FastAPI
COMPANY_ID = "FLX-001"
SESSION_ID = "pi-kiosk-001"

PIR_GPIO = 17
SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 4

def post_json(path: str, payload: dict, timeout=30):
    url = f"{TOTEM_BASE_URL}{path}"
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def activate():
    payload = {"company_id": COMPANY_ID, "session_id": SESSION_ID}
    resp = post_json("/totem/activate", payload)
    print("[ACTIVATE]", resp["greeting"])
    return resp

def record_audio_wav_bytes():
    print("[AUDIO] Gravando...")
    audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16")
    sd.wait()
    print("[AUDIO] OK")
    raw = audio.tobytes()
    # aqui estamos mandando PCM cru; ideal é WAV/FLAC (ver nota abaixo)
    return raw

def interact_audio(audio_bytes: bytes):
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    payload = {
        "company_id": COMPANY_ID,
        "session_id": SESSION_ID,
        "audio_base64": audio_b64,
        "prefer_audio": False,  # depois você liga TTS
        "message": None
    }
    resp = post_json("/totem/interact", payload, timeout=60)
    print("[BOT]", resp["text"])
    print("[RECS]", json.dumps(resp["recommendations"], ensure_ascii=False))
    return resp

def interact_text(text: str):
    payload = {
        "company_id": COMPANY_ID,
        "session_id": SESSION_ID,
        "message": text,
        "prefer_audio": False,
    }
    resp = post_json("/totem/interact", payload, timeout=60)
    print("[BOT]", resp["text"])
    return resp

def main():
    pir = MotionSensor(PIR_GPIO)
    print("Aguardando presença...")

    while True:
        pir.wait_for_motion()
        print("[PIR] Presença detectada")
        activate()

        # fallback simples: digitar texto (teste rápido sem STT real)
        # interact_text("Tem promo hoje?")

        # áudio
        audio_bytes = record_audio_wav_bytes()
        interact_audio(audio_bytes)

        # pausa para não ficar retriggerando toda hora
        time.sleep(5)

if __name__ == "__main__":
    main()