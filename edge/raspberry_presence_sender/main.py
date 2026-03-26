from __future__ import annotations

import time

from edge.raspberry_presence_sender.config import (
    API_BASE_URL,
    CLEAR_DELAY_S,
    COMPANY_ID,
    DEVICE_ID,
    PIR_PIN,
    POLL_INTERVAL_S,
)
from edge.raspberry_presence_sender.pir_sensor import PirSensor
from edge.raspberry_presence_sender.sender import PresenceSender


def main() -> None:
    sensor = PirSensor(pin=PIR_PIN)
    sender = PresenceSender(api_base_url=API_BASE_URL)

    last_presence_ts = 0.0
    was_present = False

    try:
        while True:
            present = sensor.read()

            if present:
                now = time.time()

                if not was_present:
                    sender.trigger(company_id=COMPANY_ID, device_id=DEVICE_ID)
                else:
                    sender.heartbeat(company_id=COMPANY_ID, device_id=DEVICE_ID)

                was_present = True
                last_presence_ts = now

            else:
                if was_present and (time.time() - last_presence_ts) >= CLEAR_DELAY_S:
                    sender.clear(company_id=COMPANY_ID, device_id=DEVICE_ID)
                    was_present = False

            time.sleep(POLL_INTERVAL_S)

    finally:
        sensor.cleanup()


if __name__ == "__main__":
    main()
