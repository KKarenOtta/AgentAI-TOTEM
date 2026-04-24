from __future__ import annotations

import time

from config import COOLDOWN_SECONDS, PIR_PIN, PRESENCE_HOLD_SECONDS
from pir_sensor import read_motion
from sender import send_trigger

SAMPLE_INTERVAL_SECONDS = 0.1
MIN_ACTIVE_RATIO = 0.35
WARMUP_SECONDS = 5


def confirm_presence_window() -> bool:
    total_samples = max(1, int(PRESENCE_HOLD_SECONDS / SAMPLE_INTERVAL_SECONDS))
    active_samples = 0

    start = time.time()
    while time.time() - start < PRESENCE_HOLD_SECONDS:
        if read_motion():
            active_samples += 1
        time.sleep(SAMPLE_INTERVAL_SECONDS)

    ratio = active_samples / total_samples

    print(
        f"Janela presença | ativos={active_samples} "
        f"total={total_samples} ratio={ratio:.2f}"
    )

    return ratio >= MIN_ACTIVE_RATIO


def main() -> None:
    print("Presence sender iniciado")
    print(f"PIR_PIN={PIR_PIN}")
    print(f"HOLD={PRESENCE_HOLD_SECONDS}s")
    print(f"COOLDOWN={COOLDOWN_SECONDS}s")
    print(f"Aguardando estabilização do PIR por {WARMUP_SECONDS}s...")

    time.sleep(WARMUP_SECONDS)

    print("Sensor estabilizado. Monitorando presença...")

    last_trigger_time = 0.0

    while True:
        try:
            now = time.time()

            if not read_motion():
                time.sleep(0.2)
                continue

            if now - last_trigger_time < COOLDOWN_SECONDS:
                time.sleep(0.2)
                continue

            print("Movimento detectado - validando janela do PIR...")

            if not confirm_presence_window():
                print("Presença descartada - janela insuficiente.")
                time.sleep(0.2)
                continue

            print("Presença contínua confirmada - enviando trigger...")

            if send_trigger():
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
