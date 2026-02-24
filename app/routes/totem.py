import os
from fastapi import APIRouter
from services.totem.schemas import TotemInteractRequest, TotemInteractResponse
from services.totem.orchestrator import TotemOrchestrator

router = APIRouter(prefix="/totem", tags=["totem"])

orchestrator = TotemOrchestrator(
    hugging_key=os.getenv("HUGGING_FACE")
)

@router.post("/interact", response_model=TotemInteractResponse)
def totem_interact(req: TotemInteractRequest):
    profile_dict = req.profile.model_dump() if req.profile else None

    text, recs, audio_path, metric, idioma = orchestrator.interact(
        company_id=req.company_id,
        session_id=req.session_id,
        pergunta=req.message,
        profile=profile_dict,
        prefer_audio=req.prefer_audio,
    )

    return TotemInteractResponse(
        session_id=req.session_id,
        language=idioma,
        text=text,
        recommendations=recs,
        audio_file=audio_path,
        metrics=metric,
    )