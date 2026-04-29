from __future__ import annotations

import base64
import boto3
import os


class RekognitionAdapter:

    def __init__(self):
        self.client = boto3.client(
            "rekognition",
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    def detect_human(self, image_base64: str) -> bool:
        try:
            image_bytes = base64.b64decode(image_base64)

            response = self.client.detect_faces(
                Image={"Bytes": image_bytes},
                Attributes=["DEFAULT"]
            )

            faces = response.get("FaceDetails", [])

            return len(faces) > 0

        except Exception as e:
            print("Rekognition error:", e)
            return False
