import base64
import os
import subprocess
import time

from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, JPEG_QUALITY

OUTPUT_PATH = "/tmp/last_capture.jpg"


def capture_image_base64() -> str | None:
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

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )

        print("[DEBUG stdout]:", result.stdout.decode(errors="ignore"))
        print("[DEBUG stderr]:", result.stderr.decode(errors="ignore"))

        if result.returncode != 0:
            print("[ERRO] fswebcam falhou")
            return None

        if not os.path.exists(OUTPUT_PATH):
            print("[ERRO] imagem não foi criada")
            return None

        print("[DEBUG] imagem capturada com sucesso")

        with open(OUTPUT_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    except subprocess.TimeoutExpired:
        print("[ERRO] fswebcam travou (timeout)")
        return None
    except Exception as e:
        print(f"[ERRO inesperado]: {e}")
        return None
