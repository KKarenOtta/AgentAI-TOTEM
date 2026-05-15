import requests
from core.config.runtime import CLOUD_BASE_URL

def cloud_interact(company_id: str, session_id: str, message: str = "", audio_path: str | None = None):
    url = f"{CLOUD_BASE_URL}/cloud/interact"
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
