"""
Instalação:
pip install -r requirements-pi.txt
"""
import os
import time
import json
import uuid
from enum import Enum

import requests
from dotenv import load_dotenv

import RPi.GPIO as GPIO
import board
import busio
import adafruit_dht
import adafruit_ds3231


load_dotenv()

# API
TOTEM_API = os.getenv("TOTEM_API_URL", "http://localhost:9000/totem/interact")
COMPANY_ID = os.getenv("COMPANY_ID", "FLX-001")
PREFER_AUDIO = os.getenv("PREFER_AUDIO", "true").lower() == "true"

# GPIO / barramentos
PIN_PIR = int(os.getenv("PIR_PIN", "17"))
PIN_DHT22 = board.D4
I2C_SCL = board.SCL
I2C_SDA = board.SDA

# Temporização
PRESENCE_HOLD_SECONDS = float(os.getenv("PRESENCE_HOLD_SECONDS", "3"))
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "8"))
PIR_STABILIZATION_SECONDS = 10
MAIN_LOOP_DELAY_SECONDS = 0.1
DHT_READ_RETRIES = 3
DHT_RETRY_DELAY_SECONDS = 2

# GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_PIR, GPIO.IN)

# Sensores
dht_sensor = adafruit_dht.DHT22(PIN_DHT22, use_pulseio=False)
i2c = busio.I2C(I2C_SCL, I2C_SDA)
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
            "presence_hold_seconds": PRESENCE_HOLD_SECONDS,
        },
    }


def read_env():
    for _ in range(DHT_READ_RETRIES):
        try:
            temp_c = dht_sensor.temperature
            humidity_pct = dht_sensor.humidity

            if temp_c is not None and humidity_pct is not None:
                return temp_c, humidity_pct
        except Exception as exc:
            print("Falha ao ler DHT22:", exc)
            time.sleep(DHT_RETRY_DELAY_SECONDS)

    return None, None


def read_time_iso():
    try:
        rtc_time = rtc.datetime
        return time.strftime("%Y-%m-%dT%H:%M:%S", rtc_time)
    except Exception:
        return time.strftime("%Y-%m-%dT%H:%M:%S")


def call_backend(message: str, profile: dict, session_id: str):
    payload = {
        "company_id": COMPANY_ID,
        "session_id": session_id,
        "message": message,
        "prefer_audio": PREFER_AUDIO,
        "profile": profile,
    }
    response = requests.post(TOTEM_API, json=payload, timeout=(5, 15))
    response.raise_for_status()
    return response.json()


class SensorHub:
    def __init__(self):
        self.presence_start_time = None
        self.last_trigger_time = 0.0
        self.triggered_in_current_presence = False

    def read_presence(self) -> bool:
        return GPIO.input(PIN_PIR) == 1

    def read_env(self):
        return read_env()

    def read_timestamp(self):
        return read_time_iso()

    def read_distance(self):
        return None

    def should_aware(self, _distance=None):
        now = time.time()
        presence_detected = self.read_presence()
        in_cooldown = (now - self.last_trigger_time) < COOLDOWN_SECONDS

        if presence_detected:
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
    temp_c, humidity_pct = read_env()
    rtc_iso = read_time_iso()

    profile = estimate_profile_simple()
    profile["extra"]["temp_c"] = temp_c
    profile["extra"]["humidity_pct"] = humidity_pct
    profile["extra"]["rtc_iso"] = rtc_iso
    profile["extra"]["pir_detected"] = True
    profile["extra"]["camera_source"] = "MTM-3201"
    profile["extra"]["interaction_mode"] = "presence_confirmed_3s"

    message = "Olá! Quais ofertas e recomendações você tem para mim hoje?"

    print("\n[Presença confirmada por 3 segundos]")
    print("Session:", session_id)
    print("Perfil:", json.dumps(profile, ensure_ascii=False, indent=2))
    print("Enviando para backend...")

    try:
        response = call_backend(message, profile, session_id)
        print("\n[Resposta do backend]")
        print("Texto:", response.get("text"))
        print(
            "Recs:",
            json.dumps(response.get("recommendations"), ensure_ascii=False, indent=2),
        )
        print("Audio:", response.get("audio_file"))
    except requests.exceptions.RequestException as exc:
        print("Erro de rede/backend:", exc)
    except Exception as exc:
        print("Erro inesperado:", exc)


def main():
    print("=== Totem Sensor (Raspberry Pi 3) ===")
    print("API:", TOTEM_API)
    print("Company:", COMPANY_ID)
    print("PIR GPIO:", PIN_PIR)
    print("DHT22 GPIO:", PIN_DHT22)
    print("Presença contínua exigida:", PRESENCE_HOLD_SECONDS, "segundos")
    print("Cooldown:", COOLDOWN_SECONDS, "segundos")

    print("Aguardando estabilização do PIR...")
    time.sleep(PIR_STABILIZATION_SECONDS)
    print("Sistema pronto.")

    hub = SensorHub()

    while True:
        try:
            if hub.should_aware():
                handle_presence_trigger()

            time.sleep(MAIN_LOOP_DELAY_SECONDS)

        except KeyboardInterrupt:
            print("\nEncerrando programa...")
            break
        except Exception as exc:
            print("\nErro no loop principal:", exc)
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()