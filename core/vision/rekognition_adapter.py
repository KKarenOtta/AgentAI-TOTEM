from __future__ import annotations

import base64
import os
from typing import Any


class RekognitionAdapter:
    def __init__(self) -> None:
        self.region_name = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    def detect_human(self, image_base64: str) -> tuple[bool, dict[str, Any]]:
        try:
            import boto3
        except Exception as exc:
            return False, {
                "validation_engine": "aws_rekognition",
                "rekognition_available": False,
                "reason": f"boto3_unavailable:{type(exc).__name__}",
            }

        try:
            image_bytes = base64.b64decode(image_base64, validate=False)
            client = boto3.client("rekognition", region_name=self.region_name)

            response = client.detect_faces(
                Image={"Bytes": image_bytes},
                Attributes=["DEFAULT"],
            )

            faces = response.get("FaceDetails") or []

            return len(faces) > 0, {
                "validation_engine": "aws_rekognition",
                "rekognition_available": True,
                "rekognition_faces_detected": len(faces),
                "reason": "ok" if faces else "no_face_detected_by_rekognition",
            }

        except Exception as exc:
            return False, {
                "validation_engine": "aws_rekognition",
                "rekognition_available": True,
                "rekognition_faces_detected": 0,
                "reason": f"rekognition_error:{type(exc).__name__}",
            }
