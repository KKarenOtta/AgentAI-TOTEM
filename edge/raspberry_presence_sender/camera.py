import base64
import os
import shutil
import subprocess
import tempfile
import time

from config import (
    CAMERA_INDEX,
    CAMERA_WARMUP_SECONDS,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    JPEG_QUALITY,
)


def _file_to_base64(path: str) -> str | None:
    if not os.path.exists(path):
        return None

    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _capture_with_fswebcam(output_path: str) -> bool:
    if not shutil.which("fswebcam"):
        return False

    device = f"/dev/video{CAMERA_INDEX}"
    cmd = [
        "fswebcam",
        "-d",
        device,
        "-r",
        f"{CAMERA_WIDTH}x{CAMERA_HEIGHT}",
        "--jpeg",
        str(JPEG_QUALITY),
        "--no-banner",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Erro fswebcam:", result.stderr.strip() or result.stdout.strip())
        return False

    return os.path.exists(output_path)


def _capture_with_rpicam(output_path: str) -> bool:
    binary = shutil.which("rpicam-still")
    if not binary:
        return False

    cmd = [
        binary,
        "--output",
        output_path,
        "--timeout",
        str(int(CAMERA_WARMUP_SECONDS * 1000)),
        "--width",
        str(CAMERA_WIDTH),
        "--height",
        str(CAMERA_HEIGHT),
        "--quality",
        str(JPEG_QUALITY),
        "--nopreview",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Erro rpicam-still:", result.stderr.strip() or result.stdout.strip())
        return False

    return os.path.exists(output_path)


def _capture_with_libcamera(output_path: str) -> bool:
    binary = shutil.which("libcamera-still")
    if not binary:
        return False

    cmd = [
        binary,
        "-o",
        output_path,
        "-t",
        str(int(CAMERA_WARMUP_SECONDS * 1000)),
        "--width",
        str(CAMERA_WIDTH),
        "--height",
        str(CAMERA_HEIGHT),
        "--quality",
        str(JPEG_QUALITY),
        "--nopreview",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Erro libcamera-still:", result.stderr.strip() or result.stdout.strip())
        return False

    return os.path.exists(output_path)


def _capture_with_opencv(output_path: str) -> bool:
    try:
        import cv2
    except Exception as exc:
        print(f"OpenCV indisponível: {exc}")
        return False

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("Erro: não foi possível abrir a câmera via OpenCV")
        return False

    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        time.sleep(CAMERA_WARMUP_SECONDS)

        ok, frame = cap.read()
        if not ok or frame is None:
            print("Erro: captura via OpenCV falhou")
            return False

        encode_ok, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
        )
        if not encode_ok:
            print("Erro: falha ao codificar JPEG via OpenCV")
            return False

        with open(output_path, "wb") as f:
            f.write(buffer.tobytes())

        return True

    finally:
        cap.release()


def capture_image_base64() -> str | None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        output_path = tmp.name

    try:
        if _capture_with_fswebcam(output_path):
            return _file_to_base64(output_path)

        if _capture_with_rpicam(output_path):
            return _file_to_base64(output_path)

        if _capture_with_libcamera(output_path):
            return _file_to_base64(output_path)

        if _capture_with_opencv(output_path):
            return _file_to_base64(output_path)

        print("Erro: nenhuma estratégia de captura funcionou")
        return None

    finally:
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass
