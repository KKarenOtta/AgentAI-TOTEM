import time
import atexit

GPIO_AVAILABLE = True
BOARD_AVAILABLE = True
DHT_AVAILABLE = True

try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    GPIO_AVAILABLE = False
    GPIO = None

try:
    import board
except ModuleNotFoundError:
    BOARD_AVAILABLE = False
    board = None

try:
    import adafruit_dht
except ModuleNotFoundError:
    DHT_AVAILABLE = False
    adafruit_dht = None


LED_PIN = 18
DHT_PIN = board.D4 if BOARD_AVAILABLE else None

ULTRA_SENSORS = [
    {"name": "Esquerda", "trig": 17, "echo": 27},
    {"name": "Centro", "trig": 22, "echo": 23},
    {"name": "Direita", "trig": 24, "echo": 25},
]

ALERT_DISTANCE_CM = 8
SESSION_DISTANCE_CM = 100
INVITE_DISTANCE_CM = 200
TEMP_ALERT_HIGH = 40
TEMP_ALERT_LOW = 5
DHT_READ_INTERVAL = 3.0

HARDWARE_AVAILABLE = GPIO_AVAILABLE and BOARD_AVAILABLE and DHT_AVAILABLE

dht = None

system_data = {
    "temperature": None,
    "humidity": None,
    "ultrassons": [],
    "presence": False,
    "led": False,
    "message": "Inicializando",
    "totem_state": "espera",
    "active_sensor": None,
    "manual_led_override": False,
}

last_dht_read = 0
last_temperature = None
last_humidity = None


if HARDWARE_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)

    for sensor in ULTRA_SENSORS:
        GPIO.setup(sensor["trig"], GPIO.OUT)
        GPIO.setup(sensor["echo"], GPIO.IN)
        GPIO.output(sensor["trig"], False)

    dht = adafruit_dht.DHT22(DHT_PIN, use_pulseio=False)


def cleanup_gpio():
    if not HARDWARE_AVAILABLE:
        return

    try:
        GPIO.output(LED_PIN, GPIO.LOW)
    except Exception:
        pass

    try:
        if dht is not None:
            dht.exit()
    except Exception:
        pass

    try:
        GPIO.cleanup()
    except Exception:
        pass


atexit.register(cleanup_gpio)


def read_distance(trig, echo):
    if not HARDWARE_AVAILABLE:
        return None

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


def read_dht22(logger=None):
    global last_dht_read, last_temperature, last_humidity

    if not HARDWARE_AVAILABLE or dht is None:
        return last_temperature, last_humidity

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


def classify_distance(distance_cm):
    if distance_cm is None:
        return "espera"
    if distance_cm <= ALERT_DISTANCE_CM:
        return "alerta"
    if ALERT_DISTANCE_CM < distance_cm <= SESSION_DISTANCE_CM:
        return "sessao"
    if SESSION_DISTANCE_CM < distance_cm < INVITE_DISTANCE_CM:
        return "convite"
    return "espera"


def is_temperature_alert(temperature):
    if temperature is None:
        return False
    return temperature > TEMP_ALERT_HIGH or temperature < TEMP_ALERT_LOW


def get_message(state, temperature=None):
    if not HARDWARE_AVAILABLE:
        return "Modo cloud: hardware indisponivel neste ambiente."

    if state == "alerta":
        if temperature is not None and temperature > TEMP_ALERT_HIGH:
            return "Atencao: temperatura acima de 40 graus."
        if temperature is not None and temperature < TEMP_ALERT_LOW:
            return "Atencao: temperatura abaixo de 5 graus."
        return "Atencao: objeto muito proximo detectado."

    if state == "sessao":
        return "Ola, seja bem-vindo! Eu sou o Totem Inteligente FlexMedia, em que posso lhe ajudar?"

    if state == "convite":
        return "Chegue mais perto para iniciar o totem."

    return "Aguardando visitante"


def decide_state(sensor_results, temperature):
    if is_temperature_alert(temperature):
        return "alerta", "Temperatura"

    for item in sensor_results:
        if item["state"] == "alerta":
            return "alerta", item["sensor"]

    for item in sensor_results:
        if item["state"] == "sessao":
            return "sessao", item["sensor"]

    for item in sensor_results:
        if item["state"] == "convite":
            return "convite", item["sensor"]

    return "espera", None


def build_mock_sensor_results():
    return [
        {"sensor": "Esquerda", "distance_cm": None, "state": "espera"},
        {"sensor": "Centro", "distance_cm": None, "state": "espera"},
        {"sensor": "Direita", "distance_cm": None, "state": "espera"},
    ]


def update_system_state(logger=None):
    if not HARDWARE_AVAILABLE:
        sensor_results = build_mock_sensor_results()
        system_data["temperature"] = None
        system_data["humidity"] = None
        system_data["ultrassons"] = sensor_results
        system_data["presence"] = False
        system_data["led"] = bool(system_data["manual_led_override"])
        system_data["message"] = "Modo cloud: hardware indisponivel neste ambiente."
        system_data["totem_state"] = "espera"
        system_data["active_sensor"] = None

        return {
            "temperature": system_data["temperature"],
            "humidity": system_data["humidity"],
            "presence": system_data["presence"],
            "led": system_data["led"],
            "message": system_data["message"],
            "totem_state": system_data["totem_state"],
            "active_sensor": system_data["active_sensor"],
            "distance_sensor_1_cm": None,
            "distance_sensor_2_cm": None,
            "distance_sensor_3_cm": None,
            "ultrassons": sensor_results,
        }

    sensor_results = []

    for sensor in ULTRA_SENSORS:
        distance = read_distance(sensor["trig"], sensor["echo"])
        sensor_state = classify_distance(distance)

        sensor_results.append({
            "sensor": sensor["name"],
            "distance_cm": distance,
            "state": sensor_state,
        })

        time.sleep(0.08)

    temperature, humidity = read_dht22(logger=logger)
    totem_state, active_sensor = decide_state(sensor_results, temperature)
    message = get_message(totem_state, temperature)

    system_data["temperature"] = temperature
    system_data["humidity"] = humidity
    system_data["ultrassons"] = sensor_results
    system_data["presence"] = totem_state in ("convite", "sessao", "alerta")
    system_data["led"] = totem_state in ("convite", "sessao", "alerta")
    system_data["message"] = message
    system_data["totem_state"] = totem_state
    system_data["active_sensor"] = active_sensor

    if system_data["manual_led_override"]:
        GPIO.output(LED_PIN, GPIO.HIGH)
        system_data["led"] = True
    else:
        GPIO.output(LED_PIN, GPIO.HIGH if system_data["led"] else GPIO.LOW)

    return {
        "temperature": system_data["temperature"],
        "humidity": system_data["humidity"],
        "presence": system_data["presence"],
        "led": system_data["led"],
        "message": system_data["message"],
        "totem_state": system_data["totem_state"],
        "active_sensor": system_data["active_sensor"],
        "distance_sensor_1_cm": sensor_results[0]["distance_cm"] if len(sensor_results) > 0 else None,
        "distance_sensor_2_cm": sensor_results[1]["distance_cm"] if len(sensor_results) > 1 else None,
        "distance_sensor_3_cm": sensor_results[2]["distance_cm"] if len(sensor_results) > 2 else None,
        "ultrassons": sensor_results,
    }


def set_led_state(on):
    system_data["manual_led_override"] = on

    if HARDWARE_AVAILABLE:
        GPIO.output(LED_PIN, GPIO.HIGH if on else GPIO.LOW)
        system_data["led"] = GPIO.input(LED_PIN) == 1
    else:
        system_data["led"] = bool(on)

    return system_data["led"]


def get_public_status():
    return {
        "temperature": system_data["temperature"],
        "humidity": system_data["humidity"],
        "presence": system_data["presence"],
        "led": system_data["led"],
        "message": system_data["message"],
        "totem_state": system_data["totem_state"],
        "active_sensor": system_data["active_sensor"],
        "distance_sensor_1_cm": system_data["ultrassons"][0]["distance_cm"] if len(system_data["ultrassons"]) > 0 else None,
        "distance_sensor_2_cm": system_data["ultrassons"][1]["distance_cm"] if len(system_data["ultrassons"]) > 1 else None,
        "distance_sensor_3_cm": system_data["ultrassons"][2]["distance_cm"] if len(system_data["ultrassons"]) > 2 else None,
        "ultrassons": system_data["ultrassons"],
    }


def get_full_status():
    return system_data
