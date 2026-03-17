"""
Instalação:
pip install -r requirements-pi.txt
"""
import os
import time
import json
import uuid
import requests
from enum import Enum
from dotenv import load_dotenv
import adafruit_dht

load_dotenv()

TOTEM_API = os.getenv("TOTEM_API_URL", "http://localhost:9000/totem/interact")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001")
PREFER_AUDIO = os.getenv("PREFER_AUDIO", "true").lower() == "true"
PIR_PIN = int(os.getenv("PIR_PIN", "17"))
PRESENCE_HOLD_SECONDS = float(os.getenv("PRESENCE_HOLD_SECONDS", "3"))
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "8"))

import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

import adafruit_dht
import board
dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

import busio
import adafruit_ds3231
i2c = busio.I2C(board.SCL, board.SDA)
rtc = adafruit_ds3231.DS3231(i2c)

class Event(str, Enum):
    AWARE = "aware"
    WAKEWORD = "wakeword"
    TEXT_INPUT = "text_input"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


def beep():
    print("\a", end="", flush=True)


def estimate_profile_simple():
    return {
        "age_estimate": 28,
        "age_range": "25-34",
        "gender": "unknown",
        "confidence": 0.6,
        "segment": "new_visitor",
        "device": "totem_rpi3",
        "locale": "pt-BR",
        "extra": {
            "totem_model": "MTM-3201",
            "presence_sensor": "HC-SR501",
            "presence_hold_seconds": PRESENCE_HOLD_SECONDS
        }
    }


def read_env():
    for _ in range(3):
        try:
            temp = dht.temperature
            hum = dht.humidity
            if temp is not None and hum is not None:
                return temp, hum
        except Exception as e:
            print("Falha ao ler DHT22:", e)
            time.sleep(2)
    return None, None


def read_time_iso():
    try:
        t = rtc.datetime
        return time.strftime("%Y-%m-%dT%H:%M:%S", t)
    except Exception as e:
        #print("Falha ao ler RTC:", e)
        return time.strftime("%Y-%m-%dT%H:%M:%S")


def call_backend(message: str, profile: dict, session_id: str):
    payload = {
        "company_id": COMPANY_ID,
        "session_id": session_id,
        "message": message,
        "prefer_audio": PREFER_AUDIO,
        "profile": profile
    }
    r = requests.post(TOTEM_API, json=payload, timeout=(5, 15))
    r.raise_for_status()
    return r.json()


class SensorHub:
    def __init__(self):
        self.presence_start_time = None
        self.last_trigger_time = 0.0
        self.triggered_in_current_presence = False

    def read_presence(self) -> bool:
        return GPIO.input(PIR_PIN) == 1

    def read_env(self):
        return read_env()

    def read_timestamp(self):
        return read_time_iso()

    def read_distance(self):
        return None

    def should_aware(self, _distance=None):
        now = time.time()
        presence = self.read_presence()
        in_cooldown = (now - self.last_trigger_time) < COOLDOWN_SECONDS

        if presence:
            if self.presence_start_time is None:
                self.presence_start_time = now
                self.triggered_in_current_presence = False
                return False

            held_time = now - self.presence_start_time

            if (
                not in_cooldown
                and not self.triggered_in_current_presence
                and held_time >= PRESENCE_HOLD_SECONDS
            ):
                self.triggered_in_current_presence = True
                self.last_trigger_time = now
                return True

            return False

        self.presence_start_time = None
        self.triggered_in_current_presence = False
        return False

    def log_event(
        self,
        event: Event,
        dist=None,
        temp=None,
        hum=None,
        session_id=None,
        latency_total=None,
        latency_llm=None,
        latency_tts=None,
        extra=None,
    ):
        payload = {
            "ts": self.read_timestamp(),
            "event": event.value if isinstance(event, Event) else str(event),
            "session_id": session_id,
            "distance_m": dist,
            "temp_c": temp,
            "humidity_pct": hum,
            "latency_total": latency_total,
            "latency_llm": latency_llm,
            "latency_tts": latency_tts,
            "extra": extra or {},
        }
        print("[LOG_EVENT]", json.dumps(payload, ensure_ascii=False))

    def cleanup(self):
        GPIO.cleanup()


def handle_presence_trigger():
    session_id = f"sess-{uuid.uuid4().hex[:8]}"

    beep()
    temp, hum = read_env()
    ts = read_time_iso()

    profile = estimate_profile_simple()
    profile["extra"]["temp_c"] = temp
    profile["extra"]["humidity_pct"] = hum
    profile["extra"]["rtc_iso"] = ts
    profile["extra"]["pir_detected"] = True
    profile["extra"]["camera_source"] = "MTM-3201"
    profile["extra"]["interaction_mode"] = "presence_confirmed_3s"

    message = "Olá! Quais ofertas e recomendações você tem para mim hoje?"

    print("\n[Presença confirmada por 3 segundos]")
    print("Session:", session_id)
    print("Perfil:", json.dumps(profile, ensure_ascii=False, indent=2))
    print("Enviando para backend...")

    try:
        resp = call_backend(message, profile, session_id)
        print("\n[Resposta do backend]")
        print("Texto:", resp.get("text"))
        print("Recs:", json.dumps(resp.get("recommendations"), ensure_ascii=False, indent=2))
        print("Audio:", resp.get("audio_file"))
    except requests.exceptions.RequestException as e:
        print("Erro de rede/backend:", e)
    except Exception as e:
        print("Erro inesperado:", e)


def main():
    print("=== Totem Sensor (Raspberry Pi 3) ===")
    print("API:", TOTEM_API)
    print("Company:", COMPANY_ID)
    print("PIR GPIO:", PIR_PIN)
    print("Presença contínua exigida:", PRESENCE_HOLD_SECONDS, "segundos")
    print("Cooldown:", COOLDOWN_SECONDS, "segundos")

    print("Aguardando estabilização do PIR...")
    time.sleep(10)
    print("Sistema pronto.")

    hub = SensorHub()

    while True:
        try:
            if hub.should_aware():
                handle_presence_trigger()
            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nEncerrando programa...")
            break
        except Exception as e:
            print("\nErro no loop principal:", e)
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()