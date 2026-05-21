from __future__ import annotations

import base64
import os
import threading
import time
from pathlib import Path
from typing import Any

from infra.async_tasks.tasks import log_training_task
from infra.realtime.event_bus import publish, subscribe
from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions

from ml.semantic.retriever import ask_rag
from ml.semantic.cache import get as cache_get, set as cache_set
from ml.semantic.faq_engine import FAQEngine

from core.faq.learning import register_use
from core.sensors.climate_store import answer_climate
from core.totem.company_context import answer_from_company_context, load_company_context
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

def clean_response(text: str) -> str:
    if not text:
        return text

    return re.sub(r'https?://\S+', '', text).strip()

class TotemOrchestrator:
    def __init__(self) -> None:
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    # =========================
    # JUDGE (RESTAURADO)
    # =========================
    def _judge_response(self, question: str, answer: str, context: str) -> bool:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um avaliador de respostas de um totem. "
                            "Responda APENAS YES ou NO. "
                            "Diga YES somente se a resposta estiver correta e baseada no contexto."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"""
Pergunta: {question}

Resposta: {answer}

Contexto:
{context}
"""
                    }
                ]
            )

            return "YES" in resp.choices[0].message.content.upper()

        except Exception:
            return True  # fallback seguro para não quebrar fluxo

    # =========================
    # SYNTHESIS (RESTAURADO)
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
            temperature=0.4,
            max_tokens=250,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de um totem. "
                        "Reescreva a resposta de forma clara e natural."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
Pergunta:
{question}

Contexto:
{context}
"""
                }
            ]
        )

        return response.choices[0].message.content.strip()

    # =========================
    # FALLBACK LLM (ÚLTIMO RECURSO)
    # =========================
    def _llm_fallback(self, pergunta: str):
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            max_tokens=220,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente geral de totem. "
                        "Responda de forma natural e útil sem depender do banco local."
                    )
                },
                {
                    "role": "user",
                    "content": pergunta
                }
            ]
        )

        text = response.choices[0].message.content.strip()
        return text, 0.55, "llm_fallback", None

    # =========================
    # ROUTER
    # =========================
    @staticmethod
    def route_intent(intent: str | None) -> str:
        if not intent:
            return "general"

        if intent in ["food", "restaurant", "eat"]:
            return "rag_priority"
        if intent in ["animal", "attraction"]:
            return "faq_priority"
        if intent in ["info"]:
            return "faq_first"

        return "rag_priority"

    # =========================
    # INTERACT
    # =========================
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
            company_id, session_id, pergunta, resposta,
            idioma, prefer_audio, started,
            score, source, matched_question,
            profile, intent, intent_confidence
        )

    # =========================
    # CORE RAG PIPELINE (RESTAURADO)
    # =========================
    def _answer(self, company_id: str, pergunta: str, intent: str | None):

        if not pergunta:
            return "Pode me dizer o que você procura?", 1.0, "system", None

        climate_answer = answer_climate(company_id, pergunta)
        if climate_answer:
            return climate_answer[0], climate_answer[1], climate_answer[2], None

        cache_key = f"rag:{company_id}:{intent}:{normalize(pergunta)}"
        cached = cache_get(cache_key)
        if cached:
            return cached, 1.0, "cache", None

        local_answer, local_score, local_source = answer_from_company_context(company_id, pergunta)
        if local_answer and local_score >= 0.75:
            cache_set(cache_key, local_answer)
            return local_answer, local_score, local_source or "context", None

        faq_answer, faq_score, matched = self.faq.search(
            company_id=company_id,
            query=pergunta,
            intent=intent,
            min_score=0.75,
        )

        if faq_answer:
            cache_set(cache_key, faq_answer)
            return faq_answer, faq_score, "faq", matched

        try:
            rag_result = ask_rag(company_id, pergunta)

            if isinstance(rag_result, dict):
                chunks = rag_result.get("chunks") or []
                rag_answer = rag_result.get("answer")

                context = "\n".join(
                    f"{c.get('titulo')} - {c.get('conteudo')}"
                    for c in chunks[:5]
                )

                score = sum(c.get("score", 0.0) for c in chunks) / len(chunks) if chunks else 0.0

                if rag_answer and self._judge_response(pergunta, rag_answer, context):
                    cache_set(cache_key, rag_answer)
                    return rag_answer, score, "rag_direct", None

                if chunks:
                    final = self._synthesize_rag_answer(pergunta, rag_result)

                    if self._judge_response(pergunta, final, context):
                        cache_set(cache_key, final)
                        return final, score, "rag_synth", None

        except Exception as e:
            print("RAG ERROR:", e)

        return self._llm_fallback(pergunta)

    # =========================
    # FINALIZE (TTS GARANTIDO)
    # =========================
    def _finalize(
        self,
        company_id, session_id, pergunta, resposta,
        idioma, prefer_audio, started,
        score, source, matched_question,
        profile, intent, intent_confidence
    ):
        add_turn(session_id, pergunta, resposta)

        resposta = clean_response(resposta)

        try:
            log_training_task.delay(session_id, pergunta, resposta, score)
        except Exception:
            pass

        self._transition(session_id, Event.ANSWER_READY)

        campaigns = get_active_campaigns(company_id)
        recommendations = recommend_actions(
            profile=profile,
            active_campaigns=campaigns,
            intent=intent,
            company_id=company_id,
        )

        audio_path = None
        if prefer_audio:
            audio_path, *_ = gerar_audio(resposta, idioma)

        metric = {
            "source": source,
            "score": score,
            "intent": intent,
            "intent_confidence": float(intent_confidence or 0.0),
            "latency": round(time.perf_counter() - started, 3),
        }

        publish(
            company_id=company_id,
            event="interaction_completed",
            payload={
                "session_id": session_id,
                "response": resposta,
                "recommendations": recommendations,
                "audio_path": audio_path,
                "audio_base64": audio_to_base64(audio_path),
                "metric": metric,
            },
        )

        return resposta, recommendations, audio_path, metric, idioma

    # =========================
    # STATE
    # =========================
    def _transition(self, session_id: str, event: Event):
        try:
            current = State(get_state(session_id))
        except Exception:
            current = State.IDLE

        next_state = TRANSITIONS.get((current, event))
        if not next_state:
            return current

        set_state(session_id, next_state.value)
        return next_state
