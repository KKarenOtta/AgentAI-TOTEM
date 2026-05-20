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


class TotemOrchestrator:
    def __init__(self) -> None:
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    def on_presence_event(self, company_id: str, payload: dict[str, Any]) -> str | None:
        if not payload.get("present"):
            return None

        session_id = payload.get("session_id") or f"totem-{int(time.time() * 1000)}"
        device_id = payload.get("device_id")

        session = get_or_create_session(
            company_id=company_id,
            session_id=session_id,
            profile={
                "device_id": device_id,
                "validated": payload.get("validated"),
                "sensor_payload": payload.get("sensor_payload") or {},
                "presence_attributes": payload.get("attributes") or {},
            },
        )

        already_activated = bool(session.get("activated_at"))
        if already_activated and not payload.get("force"):
            return session_id

        session["activated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._save_profile_update(session_id, session)

        self._transition(session_id, Event.PRESENCE_DETECTED)
        self._transition(session_id, Event.SESSION_STARTED)
        self._transition(session_id, Event.GREETING_DONE)

        audio_path = None
        audio_base64 = None

        try:
            audio_path, *_ = gerar_audio(DEFAULT_GREETING, "pt")
            audio_base64 = audio_to_base64(audio_path)
        except Exception:
            audio_path = None
            audio_base64 = None

        event_payload = {
            "session_id": session_id,
            "company_id": company_id,
            "device_id": device_id,
            "message": DEFAULT_GREETING,
            "audio_path": audio_path,
            "audio_base64": audio_base64,
            "presence": payload,
        }

        publish(
            company_id=company_id,
            event="totem_activated",
            payload=event_payload,
        )

        self.metrics.save(
            {
                "event": "session_started",
                "company_id": company_id,
                "session_id": session_id,
                "device_id": device_id,
                "validated": payload.get("validated"),
                "source": "presence_orchestrator",
            }
        )

        return session_id

    def end_presence_session(self, company_id: str, session_id: str, reason: str = "presence_cleared") -> None:
        self._transition(session_id, Event.SESSION_END)

        publish(
            company_id=company_id,
            event="session_ended",
            payload={
                "company_id": company_id,
                "session_id": session_id,
                "reason": reason,
            },
        )

        self.metrics.save(
            {
                "event": "session_ended",
                "company_id": company_id,
                "session_id": session_id,
                "reason": reason,
            }
        )

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
        resposta, score, source, matched_question = self._answer(company_id, pergunta, intent)

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

        print("DEBUG LOCAL SCORE:", local_score)
        print("DEBUG LOCAL SOURCE:", local_source)

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

        print("DEBUG FAQ SCORE:", faq_score)
        print("DEBUG MATCHED QUESTION:", matched_question)

        if faq_answer:
            answer = faq_answer.strip()
            cache_set(cache_key, answer)
            return answer, faq_score, "faq", matched_question

        try:
            rag_result = ask_rag(company_id, pergunta)

            print("🔥 RAG EXECUTOU")
            print("RAG RESULT:", rag_result)

            if isinstance(rag_result, dict):
                answer = rag_result.get("answer")
                chunks = rag_result.get("chunks", [])

                rag_score = max(c.get("score", 0.0) for c in chunks) if chunks else 0.0

            if chunks:
                final_answer = self._synthesize_rag_answer(pergunta, rag_result)
                cache_set(cache_key, final_answer)
                return final_answer, float(rag_score), "rag", None
                
        except Exception as e:
            print("🔥 RAG ERROR:", str(e))

        return (
            "Não encontrei essa informação na base de conhecimento do zoológico.",
            0.0,
            "no_match",
            None,
        )

    def _llm_answer(self, company_id: str, pergunta: str, intent: str | None = None) -> str:
        context = load_company_context(company_id)
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            return "Não tenho essa informação agora."

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            intent_context = f"Intenção classificada: {intent}" if intent else "Intenção classificada: não disponível"

            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é um assistente de um totem do Zoológico de São Paulo.\n"
                            "Responda SOMENTE usando informações presentes no contexto fornecido.\n"
                            "Se a informação não estiver claramente disponível no contexto, "
                            "responda exatamente:\n"
                            "'Não encontrei essa informação na base de conhecimento do zoológico.'\n"
                            "Não invente informações.\n"
                            "Não faça suposições.\n"
                            "Não responda perguntas fora do escopo do zoológico."
                        ),
                    },
                    {
                        "role": "system",
                        "content": f"{intent_context}\n\nContexto da empresa:\n{context}",
                    },
                    {
                        "role": "user",
                        "content": pergunta,
                    },
                ],
                temperature=0.1,
                max_tokens=220,
            )

            return response.choices[0].message.content or "Não consegui responder agora."

        except Exception:
            return "Não consegui responder agora."

    def _finalize(
        self,
        company_id: str,
        session_id: str,
        pergunta: str,
        resposta: str,
        idioma: str,
        prefer_audio: bool,
        started: float,
        score: float,
        source: str,
        matched_question: str | None,
        profile: dict[str, Any],
        intent: str | None,
        intent_confidence: float,
    ):
        add_turn(session_id, pergunta, resposta)

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

        latency = round(time.perf_counter() - started, 3)

        metric = {
            "response_source": source,
            "source": source,
            "score": score,
            "latency": latency,
            "matched_question": matched_question,
            "intent": intent,
            "intent_confidence": round(float(intent_confidence or 0.0), 4),
        }

        self.metrics.save(
            {
                "event": "interaction",
                "company_id": company_id,
                "session_id": session_id,
                "question": pergunta,
                "response": resposta,
                "response_source": source,
                "matched_question": matched_question,
                "score": score,
                "latency": latency,
                "intent": intent,
                "intent_confidence": round(float(intent_confidence or 0.0), 4),
            }
        )

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

    def _transition(self, session_id: str, event: Event) -> State:
        try:
            current = State(get_state(session_id))
        except Exception:
            current = State.IDLE

        next_state = TRANSITIONS.get((current, event))
        if not next_state:
            return current

        set_state(session_id, next_state.value)
        return next_state

    @staticmethod
    def _save_profile_update(session_id: str, session: dict[str, Any]) -> None:
        from core.totem.session_store import _save

        _save(session_id, session)


def start_presence_listener() -> None:
    enabled = os.getenv("TOTEM_PRESENCE_LISTENER_ENABLED", "false").strip().lower() in {"1", "true", "yes"}

    if not enabled:
        return

    global _LISTENER_STARTED

    with _LISTENER_LOCK:
        if _LISTENER_STARTED:
            return

        _LISTENER_STARTED = True

    def loop() -> None:
        company_id = os.getenv("DEFAULT_COMPANY_ID", "FLX-001")
        orchestrator = TotemOrchestrator()

        while True:
            try:
                q = subscribe(company_id)

                while True:
                    event = q.get(timeout=30)
                    event_type = event.get("type")

                    if event_type == "presence_triggered":
                        orchestrator.on_presence_event(company_id, event.get("payload") or {})

            except Exception:
                time.sleep(2)

    thread = threading.Thread(
        target=loop,
        daemon=True,
        name="totem-presence-listener",
    )
    thread.start()
    
def _synthesize_rag_answer(self, question: str, rag_result: dict) -> str:
    from openai import OpenAI
    import os

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    context = "\n\n".join(
        f"- {c['titulo']}: {c['conteudo']}"
        for c in rag_result.get("chunks", [])
    )

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um assistente de um totem de zoológico. "
                    "Sua função é transformar informações técnicas em respostas naturais, claras e amigáveis. "
                    "Nunca copie o contexto literalmente. "
                    "Sempre reescreva com fluidez para o usuário final."
                )
            },
            {
                "role": "user",
                "content": f"""
Pergunta do usuário:
{question}

Informações recuperadas:
{context}

Responda de forma natural e útil para o visitante.
"""
            }
        ],
        temperature=0.4,
        max_tokens=250,
    )

    return response.choices[0].message.content.strip()
