import base64

from fastapi import APIRouter, File, Form, UploadFile

from core.totem.stt import stt_from_base64
from core.tts.tts import gerar_audio

router = APIRouter()


@router.post("/cloud/interact")
async def cloud_interact(
    company_id: str = Form(...),
    session_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile | None = File(None),
):
    transcript = (message or "").strip()
    stt_latency = 0
    stt_source = "text"

    if file is not None:
        audio_bytes = await file.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        transcript, stt_latency, stt_source = stt_from_base64(audio_b64)

    answer_text = f"Recebido na cloud. company_id={company_id}, session_id={session_id}, texto={transcript}"

    audio_path, tts_source, tts_status, tts_error, tts_latency = gerar_audio(answer_text)

    return {
        "transcript": transcript,
        "answer_text": answer_text,
        "audio_path": audio_path,
        "language": "pt",
        "stt_source": stt_source,
        "stt_latency": stt_latency,
        "tts_source": tts_source,
        "tts_status": tts_status,
        "tts_error": tts_error,
        "tts_latency": tts_latency,
    }
