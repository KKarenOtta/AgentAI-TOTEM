import base64
from fastapi import APIRouter, UploadFile, File, Form

from core.totem.orchestrator import TotemOrchestrator
from core.totem.stt import stt_from_base64

router = APIRouter()
orchestrator = TotemOrchestrator()

@router.post("/cloud/interact")
async def cloud_interact(
    company_id: str = Form(...),
    session_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile | None = File(None),
):
    transcript = message.strip()
    stt_latency = 0
    stt_source = "text"

    if file is not None:
        audio_bytes = await file.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        transcript, stt_latency, stt_source = stt_from_base64(audio_b64)

    resposta, recommendations, audio_path, metric, idioma = orchestrator.interact(
        company_id=company_id,
        session_id=session_id,
        pergunta=transcript,
        profile={},
        prefer_audio=True,
    )

    return {
        "transcript": transcript,
        "answer_text": resposta,
        "audio_path": audio_path,
        "metric": metric,
        "language": idioma,
        "stt_source": stt_source,
        "stt_latency": stt_latency,
    }
