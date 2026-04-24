from __future__ import annotations

import base64
import os

from repositories.presence_repository import PresenceRepository


_presence_repo = PresenceRepository()


class PresenceService:
    def __init__(self) -> None:
        self.require_image = os.getenv("PRESENCE_REQUIRE_IMAGE", "true").strip().lower() == "true"
        self.require_human_validation = (
            os.getenv("PRESENCE_REQUIRE_HUMAN_VALIDATION", "true").strip().lower() == "true"
        )

    def trigger(
        self,
        company_id: str,
        device_id: str,
        image_base64: str | None = None,
    ) -> dict:
        attributes: dict = {
            "validation_engine": "opencv_haar_v2",
            "human_validated": False,
            "faces_detected": 0,
            "profiles_detected": 0,
            "image_received": bool(image_base64),
            "require_image": self.require_image,
            "require_human_validation": self.require_human_validation,
        }

        if self.require_image and not image_base64:
            return {
                "company_id": company_id,
                "device_id": device_id,
                "present": False,
                "reason": "image_required",
                "attributes": attributes,
            }

        if image_base64:
            validated, detected_attributes = self._validate_human_with_image(image_base64)
            attributes.update(detected_attributes)
        else:
            validated = False

        if self.require_human_validation and not validated:
            return {
                "company_id": company_id,
                "device_id": device_id,
                "present": False,
                "reason": "human_not_validated",
                "attributes": attributes,
            }

        state = _presence_repo.set_present(company_id=company_id, device_id=device_id)
        state["attributes"] = attributes

        self._publish(company_id=company_id, event="presence_triggered", payload=state)
        return state

    def heartbeat(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.heartbeat(company_id=company_id, device_id=device_id)
        self._publish(company_id=company_id, event="presence_heartbeat", payload=state)
        return state

    def clear(self, company_id: str, device_id: str) -> dict:
        state = _presence_repo.clear(company_id=company_id, device_id=device_id)
        self._publish(company_id=company_id, event="presence_cleared", payload=state)
        return state

    def _validate_human_with_image(self, image_base64: str) -> tuple[bool, dict]:
        try:
            import cv2
            import numpy as np
        except Exception as exc:
            return False, {
                "validation_engine": "opencv_haar_v2",
                "human_validated": False,
                "faces_detected": 0,
                "profiles_detected": 0,
                "reason": f"opencv_unavailable: {exc}",
            }

        try:
            image_bytes = base64.b64decode(image_base64, validate=False)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                return False, {
                    "validation_engine": "opencv_haar_v2",
                    "human_validated": False,
                    "faces_detected": 0,
                    "profiles_detected": 0,
                    "reason": "invalid_image",
                }

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)

            frontal_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"

            frontal_cascade = cv2.CascadeClassifier(frontal_path)
            profile_cascade = cv2.CascadeClassifier(profile_path)

            faces = frontal_cascade.detectMultiScale(
                gray,
                scaleFactor=1.10,
                minNeighbors=4,
                minSize=(30, 30),
            )

            profiles = profile_cascade.detectMultiScale(
                gray,
                scaleFactor=1.10,
                minNeighbors=4,
                minSize=(30, 30),
            )

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

    @staticmethod
    def _publish(company_id: str, event: str, payload: dict) -> None:
        try:
            from services.realtime.event_bus import publish  # type: ignore
            publish(company_id=company_id, event=event, payload=payload)
        except Exception:
            return
