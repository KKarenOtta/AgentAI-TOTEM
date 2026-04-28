from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import RPi.GPIO as GPIO


@dataclass(frozen=True)
class UltrasonicSensorConfig:
    name: str
    trig: int
    echo: int


class UltrasonicPresenceDetector:
    def __init__(
        self,
        sensors: list[UltrasonicSensorConfig],
        distance_trigger_cm: float,
        min_approach_drop_cm: float,
        history_size: int = 5,
        read_timeout_s: float = 0.03,
    ) -> None:
        self.sensors = sensors
        self.distance_trigger_cm = distance_trigger_cm
        self.min_approach_drop_cm = min_approach_drop_cm
        self.read_timeout_s = read_timeout_s
        self.history: dict[str, deque[float | None]] = {
            sensor.name: deque(maxlen=history_size) for sensor in sensors
        }

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for sensor in sensors:
            GPIO.setup(sensor.trig, GPIO.OUT)
            GPIO.setup(sensor.echo, GPIO.IN)
            GPIO.output(sensor.trig, False)

    def read_state(self) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        active_sensor: str | None = None
        closest_distance: float | None = None
        approaching_detected = False
        in_range_detected = False

        for sensor in self.sensors:
            distance = self._read_distance(sensor.trig, sensor.echo)
            self.history[sensor.name].append(distance)

            approaching = self._is_approaching(sensor.name)
            in_range = distance is not None and distance <= self.distance_trigger_cm

            if approaching:
                approaching_detected = True

            if in_range:
                in_range_detected = True

            if distance is not None and (
                closest_distance is None or distance < closest_distance
            ):
                closest_distance = distance
                active_sensor = sensor.name

            results.append(
                {
                    "sensor": sensor.name,
                    "distance_cm": distance,
                    "approaching": approaching,
                    "in_range": in_range,
                }
            )

            time.sleep(0.05)

        confidence = self._confidence(
            approaching=approaching_detected,
            in_range=in_range_detected,
            distance_cm=closest_distance,
        )

        return {
            "present": approaching_detected or in_range_detected,
            "approaching": approaching_detected,
            "in_range": in_range_detected,
            "active_sensor": active_sensor,
            "distance_cm": closest_distance,
            "confidence": confidence,
            "sensors": results,
        }

    def cleanup(self) -> None:
        GPIO.cleanup()

    def _read_distance(self, trig: int, echo: int) -> float | None:
        GPIO.output(trig, False)
        time.sleep(0.01)

        GPIO.output(trig, True)
        time.sleep(0.00001)
        GPIO.output(trig, False)

        timeout_start = time.time()
        pulse_start = timeout_start

        while GPIO.input(echo) == 0:
            pulse_start = time.time()
            if pulse_start - timeout_start > self.read_timeout_s:
                return None

        timeout_end = time.time()
        pulse_end = timeout_end

        while GPIO.input(echo) == 1:
            pulse_end = time.time()
            if pulse_end - timeout_end > self.read_timeout_s:
                return None

        distance_cm = round((pulse_end - pulse_start) * 17150, 2)

        if distance_cm <= 0 or distance_cm > 400:
            return None

        return distance_cm

    def _is_approaching(self, sensor_name: str) -> bool:
        valid = [value for value in self.history[sensor_name] if value is not None]

        if len(valid) < 3:
            return False

        d1, d2, d3 = valid[-3], valid[-2], valid[-1]
        descending = d1 > d2 > d3
        total_drop = d1 - d3
        in_range = d3 <= self.distance_trigger_cm

        return descending and total_drop >= self.min_approach_drop_cm and in_range

    def _confidence(
        self,
        approaching: bool,
        in_range: bool,
        distance_cm: float | None,
    ) -> float:
        score = 0.0

        if in_range:
            score += 0.45

        if approaching:
            score += 0.35

        if distance_cm is not None:
            if distance_cm <= 60:
                score += 0.20
            elif distance_cm <= self.distance_trigger_cm:
                score += 0.10

        return round(min(score, 1.0), 2)
