from __future__ import annotations

import base64
import os
import time
from typing import Any

from infra.realtime.event_bus import publish
from repositories.presence_repository import PresenceRepository

from core.sensors.climate_store import save_climate
# from core.totem.orchestrator import TotemOrchestrator
from core.vision.rekognition_adapter import RekognitionAdapter


def _get_orchestrator():
    from core.totem.orchestrator import TotemOrchestrator
    return TotemOrchestrator()
    
_presence_repo = PresenceRepository()
_orchestrator = _get_orchestrator()


class PresenceService:
    def __init__(self) -> None:
        self.require_image = os.getenv("PRESENCE_REQUIRE_IMAGE", "true").strip().lower() == "true"
        self.require_human_validation = os.getenv("PRESENCE_REQUIRE_HUMAN_VALIDATION", "true").strip().lower() == "true"
        self.rekognition = RekognitionAdapter()

    def trigger(
        self,
        company_id: str,
        device_id: str,
        image_base64: str | None = None,
        sensor_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        company_id = company_id.strip()
        device_id = device_id.strip()
        sensor_payload = sensor_payload or {}

        save_climate(company_id, device_id, sensor_payload)

        attributes = self._base_attributes(sensor_payload=sensor_payload, image_base64=image_base64)

        if self.require_image and not image_base64:
            return self._rejected(
                company_id=company_id,
                device_id=device_id,
                reason="image_required",
                attributes=attributes,
            )

        validated = not self.require_human_validation

        if image_base64:
            validated, local_attrs = self._validate_human_with_image(image_base64)
            attributes.update(local_attrs)

            if self.require_human_validation and not validated:
                aws_validated, aws_attrs = self.rekognition.detect_human(image_base64)
                attributes["rekognition"] = aws_attrs

                if aws_validated:
                    validated = True
                    attributes["human_validated"] = True
                    attributes["validation_engine"] = "aws_rekognition_fallback"
                    attributes["reason"] = "ok"

        if self.require_human_validation and not validated:
            return self._rejected(
                company_id=company_id,
                device_id=device_id,
                reason="human_not_validated",
                attributes=attributes,
            )

        session_id = _presence_repo.active_session(company_id, device_id)
        if not session_id:
            session_id = self._new_session_id()

        attributes["human_validated"] = bool(validated)

        attributes["human_validated"] = bool(validated)

        state = _presence_repo.set_present(
            company_id=company_id,
            device_id=device_id,
            session_id=session_id,
            attributes=attributes,
            sensor_payload=sensor_payload,
        )

        publish(company_id=company_id, event="presence_detected", payload=state)

        if state.get("is_new_session"):
            _orchestrator.on_presence_event(company_id=company_id, payload=state)

        return state

    def heartbeat(self, company_id: str, device_id: str) -> dict[str, Any]:
        company_id = company_id.strip()
        device_id = device_id.strip()

        state = _presence_repo.heartbeat(company_id=company_id, device_id=device_id)
        publish(company_id=company_id, event="presence_heartbeat", payload=state)
        return state

    def clear(self, company_id: str, device_id: str) -> dict[str, Any]:
        company_id = company_id.strip()
        device_id = device_id.strip()

        state = _presence_repo.clear(company_id=company_id, device_id=device_id)
        publish(company_id=company_id, event="presence_cleared", payload=state)

        session_id = state.get("session_id")
        if session_id:
            _orchestrator.end_presence_session(
                company_id=company_id,
                session_id=session_id,
                reason="presence_cleared",
            )

        return state

    def _base_attributes(
        self,
        sensor_payload: dict[str, Any],
        image_base64: str | None,
    ) -> dict[str, Any]:
        return {
            "validation_engine": "opencv_haar_v2",
            "human_validated": False,
            "faces_detected": 0,
            "profiles_detected": 0,
            "image_received": bool(image_base64),
            "require_image": self.require_image,
            "require_human_validation": self.require_human_validation,
            "sensor_payload": sensor_payload,
        }

    def _rejected(
        self,
        company_id: str,
        device_id: str,
        reason: str,
        attributes: dict[str, Any],
    ) -> dict[str, Any]:
        state = {
            "company_id": company_id,
            "device_id": device_id,
            "present": False,
            "reason": reason,
            "attributes": attributes,
            "is_new_session": False,
            "is_duplicate": False,
        }
        publish(company_id=company_id, event="presence_rejected", payload=state)
        return state

    def _validate_human_with_image(self, image_base64: str) -> tuple[bool, dict[str, Any]]:
        try:
            import cv2
            import numpy as np
        except Exception as exc:
            return False, {
                "validation_engine": "opencv_haar_v2",
                "human_validated": False,
                "faces_detected": 0,
                "profiles_detected": 0,
                "reason": f"opencv_unavailable:{type(exc).__name__}",
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
                "reason": f"validation_error:{type(exc).__name__}",
            }

    @staticmethod
    def _new_session_id() -> str:
        return f"totem-{int(time.time() * 1000)}"
