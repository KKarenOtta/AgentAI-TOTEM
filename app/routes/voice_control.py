from fastapi import APIRouter
import requests

router = APIRouter(prefix="/api/voice", tags=["voice"])

RASP_URL = "http://192.168.15.15:8001"


@router.post("/capture")
def capture(session_id: str):
    try:
        requests.post(
            f"{RASP_URL}/capture",
            json={"session_id": session_id},
            timeout=90,
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
