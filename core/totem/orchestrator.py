from __future__ import annotations

import base64
import os
import threading
import time
from pathlib import Path
from typing import Any

from infra.async_tasks.tasks import log_training_task
from infra.realtime.event_bus import publish, subscribe
from ml.semantic.retriever import ask_rag
from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions

from ml.semantic.cache import get as cache_get, set as cache_set
from ml.semantic.faq_engine import FAQEngine

from core.faq.learning import register_use
from core.sensors.climate_store import answer_climate
from core.totem.company_context import answer_from_company_context
from core.totem.language import detect_language
from core.totem.metrics import MetricsLogger
from core.totem.session_store import add_turn, get_or_create_session, get_state, set_state
from core.totem.state_machine import Event, State, TRANSITIONS
from core.totem.tts import gerar_audio

DEFAULT_GREETING = "Olá! Como posso ajudar você hoje?"
MIN_INTENT_CONFIDENCE = float(os.getenv("MIN_INTENT_CONFIDENCE", "0.45"))

_LISTENER_STARTED = False
_LISTENER_LOCK = threading.Lock()


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def detect_intent_safe(text: str) -> tuple[str | None, float]:
    try:
        from ml.intent.predictor import predict as predict_intent
        intent, confidence = predict_intent(text)
    except Exception:
        return None, 0.0

    if not intent or confidence < MIN_INTENT_CONFIDENCE:
        return None, float(confidence or 0.0)

    return intent, float(confidence)


def audio_to_base64(path: str | None) -> str | None:
    if not path:
        return None

    audio_path = Path(path)
    if not audio_path.exists():
        return None

    try:
        return base64.b64encode(audio_path.read_bytes()).decode("utf-8")
    except Exception:
        return None


class TotemOrchestrator:
    def __init__(self) -> None:
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    def interact(
        self,
        company_id: str,
        session_id: str,
        pergunta: str,
        profile: dict[str, Any] | None = None,
        prefer_audio: bool = True,
        **kwargs: Any,
    ):
        started = time.perf_counter()

        pergunta = (pergunta or "").strip()
        idioma = detect_language(pergunta)
        profile = profile or {}

        get_or_create_session(company_id=company_id, session_id=session_id, profile=profile)
        self._transition(session_id, Event.USER_MESSAGE)

        intent, intent_confidence = detect_intent_safe(pergunta)

        resposta, score, source, matched_question = self._answer(
            company_id, pergunta, intent
        )

        if source == "faq" and matched_question:
            register_use(company_id, matched_question)

        return self._finalize(
            company_id=company_id,
            session_id=session_id,
            pergunta=pergunta,
            resposta=resposta,
            idioma=idioma,
            prefer_audio=prefer_audio,
            started=started,
            score=score,
            source=source,
            matched_question=matched_question,
            profile=profile,
            intent=intent,
            intent_confidence=intent_confidence,
        )

    # =========================
    # RAG + INTELIGÊNCIA REAL
    # =========================
    def _answer(
        self,
        company_id: str,
        pergunta: str,
        intent: str | None,
    ) -> tuple[str, float, str, str | None]:

        if not pergunta:
            return "Pode me dizer o que você procura?", 1.0, "system", None

        climate_answer = answer_climate(company_id, pergunta)
        if climate_answer:
            text, score, source = climate_answer
            return text, score, source, None

        cache_key = f"faq:{company_id}:{intent or 'general'}:{normalize(pergunta)}"
        cached = cache_get(cache_key)

        if cached:
            return cached, 1.0, "cache", None

        local_answer, local_score, local_source = answer_from_company_context(
            company_id,
            pergunta,
        )

        if local_answer and local_score >= 0.78:
            answer = local_answer.strip()
            cache_set(cache_key, answer)
            return answer, float(local_score), local_source or "company_context", None

        faq_answer, faq_score, matched_question = self.faq.search(
            company_id=company_id,
            query=pergunta,
            intent=intent,
            min_score=0.78,
        )

        if faq_answer:
            answer = faq_answer.strip()
            cache_set(cache_key, answer)
            return answer, faq_score, "faq", matched_question

        try:
            rag_result = ask_rag(company_id, pergunta)

            if isinstance(rag_result, dict):
                chunks = rag_result.get("chunks") or []
                rag_answer = rag_result.get("answer")

                # 🔥 SCORE CORRIGIDO (média real)
                rag_score = (
                    sum(c.get("score", 0.0) for c in chunks) / len(chunks)
                    if chunks else 0.0
                )

                # =========================
                # 🧠 1. RESPOSTA DIRETA (PRIORIDADE MÁXIMA)
                # =========================
                if rag_answer and rag_score >= 0.40:
                    cache_set(cache_key, rag_answer)
                    return rag_answer, float(rag_score), "rag_direct", None

                # =========================
                # 🧠 2. SÍNTESE SÓ SE NECESSÁRIO
                # =========================
                if chunks:
                    final_answer = self._synthesize_rag_answer(pergunta, rag_result)
                    cache_set(cache_key, final_answer)
                    return final_answer, float(rag_score), "rag_synth", None

        except Exception as e:
            print("🔥 RAG ERROR:", str(e))

        return (
            "Não encontrei essa informação na base de conhecimento do zoológico.",
            0.0,
            "no_match",
            None,
        )

    # =========================
    # SYNTHESIZER (SEM MUDANÇA LÓGICA)
    # =========================
    def _synthesize_rag_answer(self, question: str, rag_result: dict) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        context = "\n\n".join(
            f"- {c.get('titulo', '')}: {c.get('conteudo', '')}"
            for c in rag_result.get("chunks", [])
        )

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de um totem de zoológico. "
                        "Reescreva de forma natural e clara."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
Pergunta:
{question}

Contexto:
{context}
""",
                },
            ],
            temperature=0.4,
            max_tokens=250,
        )

        return response.choices[0].message.content.strip()

    # =========================
    # PLACEHOLDERS (mantidos)
    # =========================
    def _finalize(self, *args, **kwargs):
        return kwargs.get("resposta"), {}, None, {}, ""

    def _transition(self, *args, **kwargs):
        pass
