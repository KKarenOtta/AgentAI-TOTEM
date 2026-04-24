import base64
import os
import subprocess
import time

from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, JPEG_QUALITY

OUTPUT_PATH = "/tmp/last_capture.jpg"
LOCK_PATH = "/tmp/camera.lock"


def _acquire_lock():
    if os.path.exists(LOCK_PATH):
        return False
    with open(LOCK_PATH, "w") as f:
        f.write("1")
    return True


def _release_lock():
    if os.path.exists(LOCK_PATH):
        os.remove(LOCK_PATH)


def capture_image_base64() -> str | None:
    if not _acquire_lock():
        print("[WARN] câmera ocupada (lock ativo)")
        return None

    try:
        device = f"/dev/video{CAMERA_INDEX}"

        if os.path.exists(OUTPUT_PATH):
            os.remove(OUTPUT_PATH)

        time.sleep(0.5)

        cmd = [
            "fswebcam",
            "-d", device,
            "-r", f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
            "--jpeg", str(JPEG_QUALITY),
            "--no-banner",
            OUTPUT_PATH,
        ]

        print(f"[DEBUG] executando: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        if result.returncode != 0:
            print("[ERRO] fswebcam falhou")
            return None

        if not os.path.exists(OUTPUT_PATH):
            print("[ERRO] imagem não foi criada")
            return None

        with open(OUTPUT_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    except Exception as e:
        print(f"[ERRO câmera]: {e}")
        return None

    finally:
        time.sleep(1.5)
        _release_lock()
