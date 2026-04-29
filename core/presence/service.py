from __future__ import annotations

import base64
import os

from infra.realtime.event_bus import publish
from repositories.presence_repository import PresenceRepository
<<<<<<< HEAD
from infra.realtime.event_bus import publish

from core.vision.rekognition_adapter import RekognitionAdapter
=======
from core.sensors.climate_store import save_climate
>>>>>>> 50095310c6794ce1f9ab915a3480eabe21bdae65

_presence_repo = PresenceRepository()


class PresenceService:
    def __init__(self) -> None:
<<<<<<< HEAD
        self.require_image = os.getenv("PRESENCE_REQUIRE_IMAGE", "true").lower() == "true"
        self.require_human_validation = os.getenv("PRESENCE_REQUIRE_HUMAN_VALIDATION", "true").lower() == "true"

        self.rekognition = RekognitionAdapter()
=======
        self.require_image = os.getenv("PRESENCE_REQUIRE_IMAGE", "true").strip().lower() == "true"
        self.require_human_validation = os.getenv("PRESENCE_REQUIRE_HUMAN_VALIDATION", "true").strip().lower() == "true"
>>>>>>> 50095310c6794ce1f9ab915a3480eabe21bdae65

    def trigger(
        self,
        company_id: str,
        device_id: str,
        image_base64: str | None = None,
        sensor_payload: dict | None = None,
    ) -> dict:
<<<<<<< HEAD

        validated = False

        if self.require_image and not image_base64:
            validated = False
=======
        sensor_payload = sensor_payload or {}
        save_climate(company_id, device_id, sensor_payload)

        attributes = {
            "validation_engine": "opencv_haar_v2",
            "human_validated": False,
            "faces_detected": 0,
            "profiles_detected": 0,
            "image_received": bool(image_base64),
            "require_image": self.require_image,
            "require_human_validation": self.require_human_validation,
            "sensor_payload": sensor_payload,
        }

        if self.require_image and not image_base64:
            return {
                "company_id": company_id,
                "device_id": device_id,
                "present": False,
                "reason": "image_required",
                "attributes": attributes,
            }

        validated = False

        if image_base64:
            validated, detected_attributes = self._validate_human_with_image(image_base64)
            attributes.update(detected_attributes)
>>>>>>> 50095310c6794ce1f9ab915a3480eabe21bdae65

        if image_base64:
            validated = self._validate_local(image_base64)

<<<<<<< HEAD
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
=======
        state = _presence_repo.set_present(company_id=company_id, device_id=device_id)
        state["attributes"] = attributes
        state["validated"] = validated
        state["sensor_payload"] = sensor_payload

        publish(company_id=company_id, event="presence_detected", payload=state)
        return state

    def heartbeat(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.heartbeat(company_id=company_id, device_id=device_id)
        publish(company_id=company_id, event="presence_heartbeat", payload=state)
        return state

    def clear(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.clear(company_id=company_id, device_id=device_id)
        publish(company_id=company_id, event="presence_cleared", payload=state)
        return state

    def _validate_human_with_image(self, image_base64: str) -> tuple[bool, dict]:
>>>>>>> 50095310c6794ce1f9ab915a3480eabe21bdae65
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

<<<<<<< HEAD
            faces = face.detectMultiScale(gray, 1.1, 4)

            return len(faces) > 0

        except Exception:
            return False
=======
            frontal = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            profile = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")

            faces = frontal.detectMultiScale(gray, 1.10, 4, minSize=(30, 30))
            profiles = profile.detectMultiScale(gray, 1.10, 4, minSize=(30, 30))

            faces_detected = len(faces)
            profiles_detected = len(profiles)
            human_validated = (faces_detected + profiles_detected) > 0

            return human_validated, {
                "validation_engine": "opencv_haar_v2",
                "human_validated": human_validated,
                "faces_detected": faces_detected,
                "profiles_detected": profiles_detected,
                "reason": "ok" if human_validated else "no_face_or_profile_detected",
            }

        except Exception as exc:
            return False, {
                "validation_engine": "opencv_haar_v2",
                "human_validated": False,
                "faces_detected": 0,
                "profiles_detected": 0,
                "reason": f"validation_error: {exc}",
            }
>>>>>>> 50095310c6794ce1f9ab915a3480eabe21bdae65
