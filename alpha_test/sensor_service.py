import time
import atexit
from collections import deque
import RPi.GPIO as GPIO
import board
import adafruit_dht

LED_PIN = 18
DHT_PIN = board.D4

ULTRA_SENSORS = [
    {"name": "Esquerda", "trig": 17, "echo": 27},
    {"name": "Centro",   "trig": 22, "echo": 23},
    {"name": "Direita",  "trig": 24, "echo": 25},
]

DISTANCE_TRIGGER_CM = 100
MIN_APPROACH_DROP_CM = 15
TEMP_ALERT_LIMIT = 30
DHT_READ_INTERVAL = 3.0
SESSION_TIMEOUT_NO_PRESENCE = 8

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

for s in ULTRA_SENSORS:
    GPIO.setup(s["trig"], GPIO.OUT)
    GPIO.setup(s["echo"], GPIO.IN)
    GPIO.output(s["trig"], False)

dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)

history = {s["name"]: deque(maxlen=5) for s in ULTRA_SENSORS}

system_data = {
    "temperature": None,
    "humidity": None,
    "ultrassons": [],
    "presence": False,
    "led": False,
    "message": "Inicializando",
    "service_session_active": False,
    "last_presence_ts": None,
    "active_sensor": None,
    "manual_led_override": False
}

last_dht_read = 0
last_temperature = None
last_humidity = None


def cleanup_gpio():
    try:
        GPIO.output(LED_PIN, GPIO.LOW)
    except Exception:
        pass

    try:
        dht.exit()
    except Exception:
        pass

    GPIO.cleanup()


atexit.register(cleanup_gpio)


def read_distance(trig, echo):
    GPIO.output(trig, False)
    time.sleep(0.05)

    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)

    pulse_start = time.time()
    timeout_start = pulse_start

    while GPIO.input(echo) == 0:
        pulse_start = time.time()
        if pulse_start - timeout_start > 0.03:
            return None

    pulse_end = time.time()
    timeout_end = pulse_end

    while GPIO.input(echo) == 1:
        pulse_end = time.time()
        if pulse_end - timeout_end > 0.03:
            return None

    pulse_duration = pulse_end - pulse_start
    distance_cm = round(pulse_duration * 17150, 2)

    if distance_cm <= 0 or distance_cm > 400:
        return None

    return distance_cm


def is_approaching(sensor_name):
    valid = [v for v in history[sensor_name] if v is not None]

    if len(valid) < 3:
        return False

    d1, d2, d3 = valid[-3], valid[-2], valid[-1]
    descending = d1 > d2 > d3
    total_drop = d1 - d3
    in_range = d3 <= DISTANCE_TRIGGER_CM

    return descending and total_drop >= MIN_APPROACH_DROP_CM and in_range


def read_dht22(logger=None):
    global last_dht_read, last_temperature, last_humidity

    now = time.time()
    if now - last_dht_read < DHT_READ_INTERVAL:
        return last_temperature, last_humidity

    try:
        temperature = dht.temperature
        humidity = dht.humidity

        if temperature is not None and humidity is not None:
            last_temperature = round(temperature, 1)
            last_humidity = round(humidity, 1)

        last_dht_read = now

    except RuntimeError as e:
        if logger:
            logger.warning("Falha de leitura DHT22: %s", e)
    except Exception as e:
        if logger:
            logger.error("Erro geral no DHT22: %s", e)

    return last_temperature, last_humidity


def update_system_state(logger=None):
    sensor_results = []
    approaching_triggered = False
    in_range_detected = False
    active_sensor = None

    for s in ULTRA_SENSORS:
        dist = read_distance(s["trig"], s["echo"])
        history[s["name"]].append(dist)

        approaching = is_approaching(s["name"])
        in_range = dist is not None and dist <= DISTANCE_TRIGGER_CM

        if in_range:
            in_range_detected = True

        if approaching and active_sensor is None:
            approaching_triggered = True
            active_sensor = s["name"]

        if active_sensor is None and in_range:
            active_sensor = s["name"]

        sensor_results.append({
            "sensor": s["name"],
            "distance_cm": dist,
            "approaching": approaching,
            "in_range": in_range
        })

        time.sleep(0.08)

    temperature, humidity = read_dht22(logger=logger)
    now = time.time()

    if approaching_triggered or in_range_detected:
        system_data["last_presence_ts"] = now

        if not system_data["service_session_active"] and logger:
            logger.info("Sessao de atendimento iniciada por presenca detectada")

        system_data["service_session_active"] = True

    if system_data["service_session_active"]:
        last_seen = system_data["last_presence_ts"]
        if last_seen is not None and (now - last_seen) > SESSION_TIMEOUT_NO_PRESENCE:
            system_data["service_session_active"] = False
            if logger:
                logger.info("Sessao de atendimento encerrada por ausencia de presenca")

    system_data["active_sensor"] = active_sensor
    system_data["temperature"] = temperature
    system_data["humidity"] = humidity
    system_data["ultrassons"] = sensor_results
    system_data["presence"] = in_range_detected

    if system_data["manual_led_override"]:
        GPIO.output(LED_PIN, GPIO.HIGH)
        message = "LED em modo manual"
    else:
        if system_data["service_session_active"] and in_range_detected:
            GPIO.output(LED_PIN, GPIO.HIGH)
            message = "Presença detectada"
            if temperature is not None and temperature > TEMP_ALERT_LIMIT:
                message = "Alerta"
        else:
            GPIO.output(LED_PIN, GPIO.LOW)
            message = "Normal" if not system_data["service_session_active"] else "Atendimento em andamento"

    system_data["led"] = GPIO.input(LED_PIN) == 1
    system_data["message"] = message

    return system_data


def set_led_state(on: bool):
    system_data["manual_led_override"] = on
    GPIO.output(LED_PIN, GPIO.HIGH if on else GPIO.LOW)
    system_data["led"] = GPIO.input(LED_PIN) == 1
    return system_data["led"]


def get_public_status():
    return {
        "temperature": system_data["temperature"],
        "humidity": system_data["humidity"],
        "presence": system_data["presence"],
        "led": system_data["led"],
        "message": system_data["message"],
        "service_session_active": system_data["service_session_active"],
        "active_sensor": system_data["active_sensor"]
    }


def get_full_status():
    return system_data