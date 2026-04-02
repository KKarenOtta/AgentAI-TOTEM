import os
import base64
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from services.totem.metrics import MetricsLogger
from services.totem.schemas import (
    TotemInteractRequest,
    TotemInteractResponse,
    TotemActivateRequest,
    TotemActivateResponse,
    TotemNPSRequest,
    TotemNPSResponse,
)
from services.totem.orchestrator import TotemOrchestrator
from services.totem.session_store import get_or_create_session, increment_turn
from services.totem.stt import stt_from_base64
from services.totem.nps import save_nps

metrics_logger = MetricsLogger(path="data/metrics/metrics.jsonl")
logger = logging.getLogger("totem")
router = APIRouter(tags=["totem"])

orchestrator = TotemOrchestrator(
    hugging_key=os.getenv("HUGGING_FACE_API_KEY") or os.getenv("HUGGING_FACE")
)


def audio_file_to_base64(audio_path: str | None) -> str | None:
    audio_path = (audio_path or "").strip()
    if not audio_path:
        return None

    if not os.path.exists(audio_path):
        logger.warning("Arquivo de áudio não encontrado para conversão: %s", audio_path)
        return None

    try:
        with open(audio_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as exc:
        logger.exception("Falha ao converter áudio para base64: %s", exc)
        return None


@router.post("/activate", response_model=TotemActivateResponse)
def totem_activate(req: TotemActivateRequest) -> TotemActivateResponse:
    try:
        profile_dict = (
            req.profile.model_dump()
            if hasattr(req.profile, "model_dump")
            else (req.profile or None)
        )
        st = get_or_create_session(req.company_id, req.session_id, profile_dict)

        greeting = "Olá! Como posso te ajudar hoje?"
        language = "pt"

        return TotemActivateResponse(
            session_id=st.session_id,
            language=language,
            greeting=greeting,
            next="listening",
        )

    except Exception as exc:
        logger.exception(
            "Erro no activate (company=%s session=%s)",
            req.company_id,
            req.session_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro no activate: {type(exc).__name__}: {exc}",
        )


@router.post("/interact", response_model=TotemInteractResponse)
def totem_interact(req: TotemInteractRequest) -> TotemInteractResponse:
    try:
        profile_dict = req.profile.model_dump() if req.profile else None
        get_or_create_session(req.company_id, req.session_id, profile_dict)
        turn = increment_turn(req.session_id)

        pergunta = (req.message or "").strip()
        stt_latency = None
        stt_provider = None

        if req.audio_base64:
            pergunta, stt_latency, stt_provider = stt_from_base64(req.audio_base64)
            pergunta = (pergunta or "").strip()

        text, recs, audio_path, metric, idioma = orchestrator.interact(
            company_id=req.company_id,
            session_id=req.session_id,
            pergunta=pergunta,
            profile=profile_dict,
            prefer_audio=req.prefer_audio,
            turn=turn,
            input_mode=("audio" if req.audio_base64 else (req.input_mode or "text")),
            stt_provider=stt_provider,
            stt_latency_s=stt_latency,
            message_id=req.message_id,
        )

        audio_base64 = audio_file_to_base64(audio_path)

        return TotemInteractResponse(
            session_id=req.session_id,
            language=idioma,
            text=text,
            recommendations=recs,
            audio_base64=audio_base64,
            metrics=metric,
        )

    except Exception as exc:
        logger.exception(
            "Erro no interact (company=%s session=%s)",
            req.company_id,
            req.session_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro no interact: {type(exc).__name__}: {exc}",
        )


@router.post("/nps", response_model=TotemNPSResponse)
def totem_nps(req: TotemNPSRequest) -> TotemNPSResponse:
    try:
        if req.score < 0 or req.score > 10:
            raise HTTPException(status_code=400, detail="score deve estar entre 0 e 10")

        save_nps(req.company_id, req.session_id, req.score, req.comment)

        nps_event = {
            "event": "nps",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "company_id": req.company_id,
            "session_id": req.session_id,
            "nps_score": req.score,
            "nps_comment": req.comment,
        }

        try:
            metrics_logger.save(nps_event)
            metrics_logger.build_report()
        except Exception:
            pass

        return TotemNPSResponse(ok=True, message="Obrigado pela avaliação!")

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Erro no nps (company=%s session=%s)",
            req.company_id,
            req.session_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Erro no nps: {type(exc).__name__}: {exc}",
        )
