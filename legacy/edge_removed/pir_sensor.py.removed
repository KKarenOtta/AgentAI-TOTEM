import RPi.GPIO as GPIO
from config import PIR_PIN

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(PIR_PIN, GPIO.IN)

def read_motion() -> bool:
    """
    Retorna True se houver movimento (HIGH no PIR)
    """
    try:
        return GPIO.input(PIR_PIN) == 1
    except Exception as e:
        print(f"Erro leitura PIR: {e}")
        return False
