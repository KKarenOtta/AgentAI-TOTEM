from __future__ import annotations

try:
    import RPi.GPIO as GPIO
except Exception:  # pragma: no cover
    GPIO = None  # type: ignore


class PirSensor:
    def __init__(self, pin: int) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO não está disponível neste ambiente.")

        self.pin = pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)

    def read(self) -> bool:
        return bool(GPIO.input(self.pin))

    def cleanup(self) -> None:
        if GPIO is not None:
            GPIO.cleanup(self.pin)
