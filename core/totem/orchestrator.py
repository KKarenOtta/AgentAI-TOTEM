from __future__ import annotations

import os
import threading
import time
from typing import Any

from infra.async_tasks.tasks import log_training_task
from infra.realtime.event_bus import publish, subscribe

from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions

from ml.semantic.cache import get as cache_get, set as cache_set
from ml.semantic.faq_engine import FAQEngine

from core.faq.learning import register_use
from core.totem.company_context import answer_from_company_context, load_company_context
from core.totem.language import detect_language
from core.totem.metrics import MetricsLogger
from core.totem.session_store import add_turn, get_or_create_session, get_state, set_state
from core.totem.state_machine import Event, State, TRANSITIONS
from core.totem.tts import gerar_audio


DEFAULT_GREETING = "Olá! Como posso ajudar você hoje?"


def normalize(text: str) -> str:
    return (text or "").strip().lower()


class TotemOrchestrator:
    def __init__(self) -> None:
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    def _transition(self, session_id: str, event: Event) -> State:
        try:
            current = State(get_state(session_id))
        except Exception:
            current = State.IDLE

        next_state = TRANSITIONS.get((current, event))

        if not next_state:
            return current

        set_state(session_id, next_state.value)

        print(
            {
                "session_id": session_id,
                "from": current.value,
                "to": next_state.value,
                "event": event.value,
            }
        )

        return next_state

    def on_presence_event(self, company_id: str, payload: dict[str, Any]) -> str | None:
        if not payload.get("present"):
            return None

        session_id = f"totem-{int(time.time() * 1000)}"

        get_or_create_session(
            company_id=company_id,
            session_id=session_id,
            profile={
                "device_id": payload.get("device_id"),
                "validated": payload.get("validated"),
                "sensor_payload": payload.get("sensor_payload") or {},
            },
        )

        self._transition(session_id, Event.PRESENCE_DETECTED)
        self._transition(session_id, Event.SESSION_STARTED)
        self._transition(session_id, Event.GREETING_DONE)

        publish(
            company_id=company_id,
            event="totem_activated",
            payload={
                "session_id": session_id,
                "message": DEFAULT_GREETING,
                "presence": payload,
            },
        )

        self.metrics.save(
            {
                "event": "session_started",
                "company_id": company_id,
                "session_id": session_id,
                "device_id": payload.get("device_id"),
                "validated": payload.get("validated"),
            }
        )

        return session_id

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

        get_or_create_session(company_id=company_id, session_id=session_id, profile=profile or {})
        self._transition(session_id, Event.USER_MESSAGE)

        resposta, score, source, matched_question = self._answer(company_id, pergunta)

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
            profile=profile or {},
        )

    def _answer(self, company_id: str, pergunta: str) -> tuple[str, float, str, str | None]:
        if not pergunta:
            return "Pode me dizer o que você procura?", 1.0, "system", None

        cache_key = f"faq:{company_id}:{normalize(pergunta)}"
        cached = cache_get(cache_key)

        if cached:
            return cached, 1.0, "cache", None

        local_answer, local_score, local_source = answer_from_company_context(company_id, pergunta)

        if local_answer and local_score >= 0.35:
            answer = local_answer.strip()
            cache_set(cache_key, answer)
            return answer, float(local_score), local_source or "company_context", None

        faq_answer, faq_score, matched_question = self.faq.search(
            company_id=company_id,
            query=pergunta,
            intent=None,
            min_score=0.5,
        )

        if faq_answer:
            answer = faq_answer.strip()
            cache_set(cache_key, answer)
            return answer, faq_score, "faq", matched_question

        return self._llm_answer(company_id, pergunta), 0.55, "llm", None

    def _llm_answer(self, company_id: str, pergunta: str) -> str:
        context = load_company_context(company_id)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "Não tenho essa informação agora."

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)

            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Você é o assistente de um totem de atendimento. "
                            "Responda de forma objetiva, útil e adequada ao contexto da empresa."
                        ),
                    },
                    {
                        "role": "system",
                        "content": f"Contexto da empresa:\n{context}",
                    },
                    {
                        "role": "user",
                        "content": pergunta,
                    },
                ],
                temperature=0.2,
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
            intent=None,
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
            }
        )

        publish(
            company_id=company_id,
            event="interaction_completed",
            payload={
                "session_id": session_id,
                "response": resposta,
                "recommendations": recommendations,
                "metric": metric,
            },
        )

        return resposta, recommendations, audio_path, metric, idioma


def start_presence_listener() -> None:
    def loop() -> None:
        company_id = os.getenv("DEFAULT_COMPANY_ID", "FLX-001")
        q = subscribe(company_id)
        orchestrator = TotemOrchestrator()

        while True:
            event = q.get()

            if event.get("type") == "presence_detected":
                orchestrator.on_presence_event(company_id, event.get("payload") or {})

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
