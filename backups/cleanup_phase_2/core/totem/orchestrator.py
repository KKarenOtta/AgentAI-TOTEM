from __future__ import annotations

import time
from datetime import datetime

from infra.async_tasks.tasks import log_training_task

from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions

from ml.semantic.faq_engine import FAQEngine
from ml.semantic.auto_learn import learn
from ml.semantic.cache import get as cache_get, set as cache_set

from core.totem.language import detect_language
from core.totem.metrics import MetricsLogger
from core.totem.tts import gerar_audio
from core.totem.session_store import (
    get_session,
    set_last_intent,
    add_turn,
    get_context,
)


INTENT_MAP = {
    "1": "compra",
    "2": "horario",
    "3": "localizacao",
    "compra": "compra",
    "horario": "horario",
    "localizacao": "localizacao",
}


def detect_intent(text: str) -> str:
    text = (text or "").lower()

    if any(w in text for w in ["comprar", "compra", "loja", "blusa", "roupa", "camiseta", "presente"]):
        return "compra"

    if any(w in text for w in ["horário", "horario", "abre", "fecha", "funciona", "funcionamento"]):
        return "horario"

    if any(w in text for w in ["onde", "localização", "localizacao", "fica", "endereço", "endereco"]):
        return "localizacao"

    return "geral"


class TotemOrchestrator:
    def __init__(self, hugging_key: str | None = None):
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    def interact(
        self,
        company_id: str,
        session_id: str,
        pergunta: str,
        profile: dict | None,
        prefer_audio: bool = True,
        **kwargs,
    ):
        started = time.perf_counter()
        pergunta = (pergunta or "").strip()
        idioma = detect_language(pergunta)

        session = get_session(session_id)
        last_intent = self._get_last_intent(session)

        resolved_intent = None
        source = "unknown"
        score = 0.0

        context = get_context(session_id) or ""
        pergunta_com_contexto = f"{context} {pergunta}".strip()

        if last_intent == "awaiting_disambiguation":
            resposta, score, source, resolved_intent = self._handle_disambiguation(
                session_id=session_id,
                pergunta=pergunta,
            )
        else:
            resposta, score, source = self._answer_question(
                session_id=session_id,
                pergunta=pergunta,
                pergunta_com_contexto=pergunta_com_contexto,
            )

        return self._finalize(
            company_id=company_id,
            session_id=session_id,
            pergunta=pergunta,
            resposta=resposta,
            idioma=idioma,
            profile=profile,
            prefer_audio=prefer_audio,
            started=started,
            score=score,
            source=source,
            resolved_intent=resolved_intent,
        )

    def _answer_question(
        self,
        session_id: str,
        pergunta: str,
        pergunta_com_contexto: str,
    ) -> tuple[str, float, str]:
        cache_key = pergunta.lower()

        cached = cache_get(cache_key)
        if cached:
            return cached, 1.0, "cache"

        intent = detect_intent(pergunta)
        resposta, score = self.faq.search(pergunta_com_contexto, intent)

        if resposta:
            resposta = self._limit(resposta)

            if score >= 0.5:
                cache_set(cache_key, resposta)

            return resposta, float(score), "faq"

        set_last_intent(session_id, "awaiting_disambiguation")

        resposta = (
            "Não tenho certeza dessa informação.\n"
            "Você quis dizer:\n"
            "1) Compra\n"
            "2) Horário\n"
            "3) Localização"
        )

        return resposta, float(score or 0.0), "active_learning"

    def _handle_disambiguation(
        self,
        session_id: str,
        pergunta: str,
    ) -> tuple[str, float, str, str | None]:
        escolha = pergunta.lower().strip()

        if escolha not in INTENT_MAP:
            return "Escolha 1, 2 ou 3.", 0.0, "retry_disambiguation", None

        resolved_intent = INTENT_MAP[escolha]
        set_last_intent(session_id, None)

        resposta = self._resolve_intent(resolved_intent)

        learn(
            question=pergunta,
            intent=resolved_intent,
            answer=resposta,
        )

        return resposta, 1.0, "resolved_intent", resolved_intent

    def _finalize(
        self,
        company_id: str,
        session_id: str,
        pergunta: str,
        resposta: str,
        idioma: str,
        profile: dict | None,
        prefer_audio: bool,
        started: float,
        score: float,
        source: str,
        resolved_intent: str | None = None,
    ):
        add_turn(session_id, pergunta, resposta)

        try:
            log_training_task.delay(session_id, pergunta, resposta, score)
        except Exception:
            pass

        campaigns = get_active_campaigns(company_id)
        recs = recommend_actions(profile, campaigns) or {}

        audio_path = None
        audio_provider = None
        audio_status_code = None
        audio_error = None
        audio_latency_s = None

        if prefer_audio:
            (
                audio_path,
                audio_provider,
                audio_status_code,
                audio_error,
                audio_latency_s,
            ) = gerar_audio(resposta, idioma)

        metric = {
            "event": "interaction",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "score": score,
            "source": source,
            "response_source": source,
            "resolved_intent": resolved_intent,
            "tts_provider": audio_provider,
            "tts_status_code": audio_status_code,
            "tts_error": audio_error,
            "tts_latency_s": audio_latency_s,
            "latency": round(time.perf_counter() - started, 3),
        }

        try:
            self.metrics.save(metric)
        except Exception:
            pass

        return resposta, recs, audio_path, metric, idioma

    def _resolve_intent(self, intent: str) -> str:
        if intent == "compra":
            return "O zoológico possui lojas com lembranças. A Loja do Pinguim oferece camisetas e itens diversos."

        if intent == "horario":
            return "Consulte o site oficial do zoológico para horários atualizados."

        if intent == "localizacao":
            return "O Zoológico de São Paulo está localizado na zona sul de São Paulo."

        return "Consulte o site oficial do zoológico."

    def _limit(self, text: str) -> str:
        parts = text.split(".")
        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            return "Consulte o site oficial do zoológico."
        return ". ".join(parts[:2]) + "."

    def _get_last_intent(self, session) -> str | None:
        if not session:
            return None

        if isinstance(session, dict):
            return session.get("last_intent")

        return getattr(session, "last_intent", None)
