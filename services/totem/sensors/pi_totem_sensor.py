import os, time, json, uuid
import requests
from dotenv import load_dotenv

load_dotenv()

# ====== CONFIG ======
TOTEM_API = os.getenv("TOTEM_API_URL", "http://localhost:8000/totem/interact")
COMPANY_ID = os.getenv("COMPANY_ID", "ACME-001")
SESSION_ID = os.getenv("SESSION_ID", f"sess-{uuid.uuid4().hex[:8]}")
PREFER_AUDIO = os.getenv("PREFER_AUDIO", "true").lower() == "true"

# GPIO pins (ajuste conforme seu wiring)
PIR_PIN = int(os.getenv("PIR_PIN", "17"))  # presença (opção recomendada)

# ====== GPIO ======
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)

# ====== DHT22 ======
import adafruit_dht
import board
dht = adafruit_dht.DHT22(board.D4)  # GPIO4

# ====== RTC DS3231 ======
import busio
import adafruit_ds3231
i2c = busio.I2C(board.SCL, board.SDA)
rtc = adafruit_ds3231.DS3231(i2c)

def beep():
    # Beep simples via terminal (se você tiver buzzer real, dá pra usar PWM no GPIO18)
    print("\a", end="", flush=True)

def estimate_profile_simple():
    """
    Caminho A: perfil 'pronto' vindo do sensor.
    Aqui você pode substituir por:
    - resultado de um modelo local (camera)
    - ou dados de um formulário na tela (faixa etária etc.)
    """
    # Placeholder seguro: pede mínimo e usa 'unknown' se não houver
    # Exemplo didático (troque pelo seu pipeline real)
    return {
        "age_estimate": 28,
        "age_range": "25-34",
        "gender": "unknown",
        "confidence": 0.6,
        "segment": "new_visitor",
        "device": "totem_rpi",
        "locale": "pt-BR",
        "extra": {}
    }

def read_env():
    temp = None
    hum = None
    try:
        temp = dht.temperature
        hum = dht.humidity
    except Exception:
        pass
    return temp, hum

def read_time_iso():
    try:
        t = rtc.datetime  # struct_time
        # converte struct_time p/ ISO simples
        return time.strftime("%Y-%m-%dT%H:%M:%S", t)
    except Exception:
        return time.strftime("%Y-%m-%dT%H:%M:%S")

def call_backend(message: str, profile: dict):
    payload = {
        "company_id": COMPANY_ID,
        "session_id": SESSION_ID,
        "message": message,
        "prefer_audio": PREFER_AUDIO,
        "profile": profile
    }
    r = requests.post(TOTEM_API, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def main():
    print("=== Totem Sensor (Raspberry Pi) ===")
    print("API:", TOTEM_API)
    print("Company:", COMPANY_ID, "Session:", SESSION_ID)

    cooldown_s = 8  # evita spam quando PIR fica ativo
    last_trigger = 0

    while True:
        presence = GPIO.input(PIR_PIN) == 1
        now = time.time()

        if presence and (now - last_trigger) > cooldown_s:
            last_trigger = now
            beep()

            temp, hum = read_env()
            ts = read_time_iso()

            profile = estimate_profile_simple()
            profile["extra"]["temp_c"] = temp
            profile["extra"]["humidity_pct"] = hum
            profile["extra"]["rtc_iso"] = ts

            # Mensagem inicial (pode vir da UI touch)
            message = "Olá! Quais ofertas e recomendações você tem para mim hoje?"

            print("\n[Presença detectada]")
            print("Perfil:", profile)
            print("Enviando para backend...")

            try:
                resp = call_backend(message, profile)
                print("\n[Resposta do backend]")
                print("Texto:", resp.get("text"))
                print("Recs:", json.dumps(resp.get("recommendations"), ensure_ascii=False, indent=2))
                print("Audio:", resp.get("audio_file"))
            except Exception as e:
                print("Erro ao chamar backend:", e)

        time.sleep(0.2)

if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()