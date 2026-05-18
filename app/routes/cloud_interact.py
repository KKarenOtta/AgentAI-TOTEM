from __future__ import annotations

import base64
import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.services.aws_db_service import AWSDBService
from core.totem.orchestrator import TotemOrchestrator
from core.totem.session_store import set_last_recommendations
from core.totem.stt import stt_from_base64

logger = logging.getLogger(__name__)

router = APIRouter()
db = AWSDBService()
orchestrator = TotemOrchestrator()


def _audio_to_base64(path: str | None) -> str | None:
    if not path:
        return None

    audio_path = Path(path)
    if not audio_path.exists():
        print("DEBUG _audio_to_base64: arquivo não existe:", path)
        return None

    try:
        return base64.b64encode(audio_path.read_bytes()).decode("utf-8")
    except Exception as exc:
        print("DEBUG _audio_to_base64 erro:", repr(exc))
        logger.warning("Falha ao converter áudio para base64: %s", exc)
        return None


def _audio_url_from_path(audio_path: str | None) -> str | None:
    if not audio_path:
        return None

    audio_str = str(audio_path).replace("\\", "/")
    marker = "/static/"

    if marker in audio_str:
        return audio_str[audio_str.index(marker):]

    path_obj = Path(audio_str)
    if path_obj.exists():
        return f"/static/{path_obj.name}"

    return None


@router.post("/cloud/interact")
async def cloud_interact(
    request: Request,
    company_id: str = Form(...),
    session_id: str = Form(...),
    message: str = Form(""),
    file: UploadFile | None = File(None),
):
    print("DEBUG 1: entrou no /cloud/interact")
    print(
        "DEBUG 2: company_id =",
        company_id,
        "| session_id =",
        session_id,
        "| message =",
        repr(message),
        "| has_file =",
        file is not None,
    )

    try:
        transcript = (message or "").strip()
        stt_latency = 0
        stt_source = "text"

        print("DEBUG 3: transcript inicial =", repr(transcript))

        if file is not None:
            print("DEBUG 4: lendo arquivo enviado...")
            audio_bytes = await file.read()
            print("DEBUG 5: bytes lidos =", len(audio_bytes))

            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            print("DEBUG 6: chamando stt_from_base64...")
            transcript, stt_latency, stt_source = stt_from_base64(audio_b64)
            print(
                "DEBUG 7: retorno stt =",
                repr(transcript),
                "| latency =",
                stt_latency,
                "| source =",
                stt_source,
            )

        transcript = (transcript or "").strip()
        print("DEBUG 8: transcript final =", repr(transcript))

        print("DEBUG 9: chamando orchestrator.interact...")
        resposta, recommendations, audio_path, metric, idioma = orchestrator.interact(
            company_id=company_id,
            session_id=session_id,
            pergunta=transcript,
            profile={},
            prefer_audio=True,
        )
        print("DEBUG 10: orchestrator ok")
        print("DEBUG 11: resposta =", repr(resposta))
        print("DEBUG 12: recommendations =", recommendations)
        print("DEBUG 13: audio_path =", audio_path)
        print("DEBUG 14: metric =", metric)
        print("DEBUG 15: idioma =", idioma)

        print("DEBUG 16: garantindo sessão no banco...")
        await db.save_session_start(session_id, company_id, "DEV-A1")
        print("DEBUG 17: sessão garantida")

        print("DEBUG 18: salvando recommendations na sessão...")
        set_last_recommendations(session_id, recommendations)

        llm_meta = {
            **(metric or {}),
            "stt_source": stt_source,
            "stt_latency": stt_latency,
        }
        print("DEBUG 19: llm_meta =", llm_meta)

        print("DEBUG 20: chamando db.save_interaction...")
        await db.save_interaction(
            session_id=session_id,
            company_id=company_id,
            message_user=transcript,
            message_bot=resposta,
            response_source=(metric or {}).get("response_source"),
            response_time_ms=int(((metric or {}).get("latency") or 0) * 1000),
            language_detected=idioma,
            llm_meta=llm_meta,
        )
        print("DEBUG 21: save_interaction ok")

        audio_url = _audio_url_from_path(audio_path)
        print("DEBUG 22: audio_url =", audio_url)

        audio_b64_out = _audio_to_base64(audio_path)
        print("DEBUG 23: audio_base64 gerado =", audio_b64_out is not None)

        response_payload = {
            "status": "ok",
            "session_id": session_id,
            "transcript": transcript,
            "answer_text": resposta,
            "audio_path": audio_path,
            "audio_base64": audio_b64_out,
            "audio_url": audio_url,
            "language": idioma,
            "recommendations": recommendations,
            "stt_source": stt_source,
            "stt_latency": stt_latency,
            "metric": metric,
        }

        print("DEBUG 24: retornando sucesso")
        return response_payload

    except Exception as exc:
        print("DEBUG ERRO cloud_interact:", repr(exc))
        raise
