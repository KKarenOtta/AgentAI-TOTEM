import requests
from core.config.runtime import CLOUD_BASE_URL


def cloud_interact(company_id: str, session_id: str, message: str = "", audio_path: str | None = None):
    base_url = (CLOUD_BASE_URL or "").strip().rstrip("/")

    if not base_url.startswith("http://") and not base_url.startswith("https://"):
        raise RuntimeError(f"CLOUD_BASE_URL invalido: {CLOUD_BASE_URL!r}")

    url = f"{base_url}/cloud/interact"

    data = {
        "company_id": company_id,
        "session_id": session_id,
        "message": message,
    }

    files = None
    file_handle = None

    try:
        if audio_path:
            file_handle = open(audio_path, "rb")
            files = {"file": file_handle}

        response = requests.post(url, data=data, files=files, timeout=90)
        response.raise_for_status()
        return response.json()
    finally:
        if file_handle:
            file_handle.close()
