from __future__ import annotations

import atexit
import time
from typing import Any

from config import (
    COOLDOWN_SECONDS,
    DISTANCE_TRIGGER_CM,
    MIN_ACTIVE_RATIO,
    MIN_APPROACH_DROP_CM,
    PRESENCE_HOLD_SECONDS,
    SAMPLE_INTERVAL_SECONDS,
    ULTRASONIC_SENSORS,
    WARMUP_SECONDS,
)
from sender import send_trigger
from edge.sensors.ultrasonic_presence import (
    UltrasonicPresenceDetector,
    UltrasonicSensorConfig,
)


def build_detector() -> UltrasonicPresenceDetector:
    sensors = [
        UltrasonicSensorConfig(
            name=item["name"],
            trig=item["trig"],
            echo=item["echo"],
        )
        for item in ULTRASONIC_SENSORS
    ]

    return UltrasonicPresenceDetector(
        sensors=sensors,
        distance_trigger_cm=DISTANCE_TRIGGER_CM,
        min_approach_drop_cm=MIN_APPROACH_DROP_CM,
    )


def confirm_presence_window(detector: UltrasonicPresenceDetector) -> dict[str, Any] | None:
    total_samples = max(1, int(PRESENCE_HOLD_SECONDS / SAMPLE_INTERVAL_SECONDS))
    active_samples = 0
    best_state: dict[str, Any] | None = None
    best_confidence = 0.0

    start = time.time()
    while time.time() - start < PRESENCE_HOLD_SECONDS:
        state = detector.read_state()

        if state["present"]:
            active_samples += 1

        confidence = float(state.get("confidence") or 0)
        if confidence >= best_confidence:
            best_confidence = confidence
            best_state = state

        time.sleep(SAMPLE_INTERVAL_SECONDS)

    ratio = active_samples / total_samples

    print(
        "Janela ultrassom | "
        f"ativos={active_samples} total={total_samples} "
        f"ratio={ratio:.2f} confidence={best_confidence:.2f}"
    )

    if ratio < MIN_ACTIVE_RATIO:
        return None

    return best_state


def main() -> None:
    print("Presence sender iniciado")
    print("Modo: ultrassom + câmera")
    print(f"HOLD={PRESENCE_HOLD_SECONDS}s")
    print(f"COOLDOWN={COOLDOWN_SECONDS}s")
    print(f"Aguardando estabilização por {WARMUP_SECONDS}s...")

    detector = build_detector()
    atexit.register(detector.cleanup)

    time.sleep(WARMUP_SECONDS)

    print("Sensores estabilizados. Monitorando presença...")

    last_trigger_time = 0.0

    while True:
        try:
            now = time.time()

            if now - last_trigger_time < COOLDOWN_SECONDS:
                time.sleep(0.2)
                continue

            state = detector.read_state()

            if not state["present"]:
                time.sleep(0.2)
                continue

            print(
                "Possível presença detectada | "
                f"sensor={state.get('active_sensor')} "
                f"dist={state.get('distance_cm')} "
                f"approaching={state.get('approaching')} "
                f"confidence={state.get('confidence')}"
            )

            confirmed_state = confirm_presence_window(detector)

            if not confirmed_state:
                print("Presença descartada - janela insuficiente.")
                time.sleep(0.2)
                continue

            print("Presença contínua confirmada - capturando imagem e enviando trigger...")

            if send_trigger(confirmed_state):
                print("Trigger aceito pela API.")
                last_trigger_time = time.time()
            else:
                print("Trigger rejeitado ou falhou.")

            time.sleep(0.2)

        except KeyboardInterrupt:
            print("Encerrado manualmente.")
            break

        except Exception as exc:
            print(f"[ERRO LOOP]: {exc}")
            time.sleep(1)


if __name__ == "__main__":
    main()
