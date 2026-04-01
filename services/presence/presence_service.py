from __future__ import annotations

import base64

from repositories.presence_repository import PresenceRepository


_presence_repo = PresenceRepository()


class PresenceService:
    def trigger(
        self,
        company_id: str,
        device_id: str,
        image_base64: str | None = None,
    ) -> dict:
        attributes: dict = {
            "validation_engine": "opencv_haar_v1",
            "human_validated": False,
            "faces_detected": 0,
        }

        if not image_base64:
            return {
                "company_id": company_id,
                "device_id": device_id,
                "present": False,
                "reason": "image_required",
                "attributes": attributes,
            }

        validated, attributes = self._validate_human_with_image(image_base64)

        if not validated:
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
                "validation_engine": "opencv_haar_v1",
                "human_validated": False,
                "faces_detected": 0,
                "reason": f"opencv_unavailable: {exc}",
            }

        try:
            image_bytes = base64.b64decode(image_base64, validate=False)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                return False, {
                    "validation_engine": "opencv_haar_v1",
                    "human_validated": False,
                    "faces_detected": 0,
                    "reason": "invalid_image",
                }

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )

            faces_detected = len(faces)

            return faces_detected > 0, {
                "validation_engine": "opencv_haar_v1",
                "human_validated": faces_detected > 0,
                "faces_detected": faces_detected,
            }

        except Exception as exc:
            return False, {
                "validation_engine": "opencv_haar_v1",
                "human_validated": False,
                "faces_detected": 0,
                "reason": f"validation_error: {exc}",
            }

    @staticmethod
    def _publish(company_id: str, event: str, payload: dict) -> None:
        try:
            from services.realtime.event_bus import publish  # type: ignore
            publish(company_id=company_id, event=event, payload=payload)
        except Exception:
            return
