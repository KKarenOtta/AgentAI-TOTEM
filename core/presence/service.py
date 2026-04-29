from __future__ import annotations

import base64
import os

from repositories.presence_repository import PresenceRepository
from infra.realtime.event_bus import publish

from core.vision.rekognition_adapter import RekognitionAdapter

_presence_repo = PresenceRepository()


class PresenceService:
    def __init__(self) -> None:
        self.require_image = os.getenv("PRESENCE_REQUIRE_IMAGE", "true").lower() == "true"
        self.require_human_validation = os.getenv("PRESENCE_REQUIRE_HUMAN_VALIDATION", "true").lower() == "true"

        self.rekognition = RekognitionAdapter()

    def trigger(
        self,
        company_id: str,
        device_id: str,
        image_base64: str | None = None,
        sensor_payload: dict | None = None,
    ) -> dict:

        validated = False

        if self.require_image and not image_base64:
            validated = False

        if image_base64:
            validated = self._validate_local(image_base64)

            # 🔥 fallback AWS
            if not validated:
                validated = self.rekognition.detect_human(image_base64)

        state = _presence_repo.set_present(company_id, device_id)
        state["validated"] = validated
        state["sensor_payload"] = sensor_payload or {}

        publish(
            company_id=company_id,
            event="presence_detected",
            payload=state
        )

        return state

    def _validate_local(self, image_base64: str) -> bool:
        try:
            import cv2
            import numpy as np

            img = base64.b64decode(image_base64)
            arr = np.frombuffer(img, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if image is None:
                return False

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

            faces = face.detectMultiScale(gray, 1.1, 4)

            return len(faces) > 0

        except Exception:
            return False
