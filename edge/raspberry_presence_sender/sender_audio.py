import requests

API_URL = "http://52.201.76.45:8000/api/audio/transcribe"


def send_audio(file_path: str) -> str | None:
    print("[AUDIO] enviando para AWS...")

    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(API_URL, files=files)

        if response.status_code != 200:
            print("[ERRO] falha na API:", response.text)
            return None

        data = response.json()
        return data.get("text")

    except Exception as e:
        print("[ERRO]", e)
        return None
