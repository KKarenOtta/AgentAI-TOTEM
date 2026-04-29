from __future__ import annotations

import os
import time
from typing import Any

from infra.async_tasks.tasks import log_training_task
from infra.realtime.event_bus import publish

from ml.semantic.cache import get as cache_get, set as cache_set
from ml.semantic.faq_engine import FAQEngine

from core.totem.company_context import answer_from_company_context, load_company_context
from core.totem.language import detect_language
from core.totem.metrics import MetricsLogger
from core.totem.session_store import add_turn, get_state, set_state, get_or_create_session
from core.totem.tts import gerar_audio
from core.sensors.climate_store import answer_climate

# NOVOS IMPORTS
from core.totem.state_machine import State, Event, TRANSITIONS
from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions


DEFAULT_SITE = "https://zoologico.com.br"
DEFAULT_MAP_URL = "https://zoologico.com.br/sobre/mapa-zoo-sao-paulo"


def normalize(text: str) -> str:
    return (text or "").strip().lower()


class TotemOrchestrator:
    def __init__(self) -> None:
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    # =========================
    # STATE MACHINE CORE
    # =========================
    def _transition(self, session_id: str, event: Event):
        current = State(get_state(session_id))
        next_state = TRANSITIONS.get((current, event))

        if not next_state:
            return current

        set_state(session_id, next_state.value)

        print({
            "session_id": session_id,
            "from": current.value,
            "to": next_state.value,
            "event": event.value,
        })

        return next_state

    # =========================
    # PRESENCE ENTRYPOINT
    # =========================
    def handle_presence_event(self, company_id: str, payload: dict):

        if not payload.get("present"):
            return

        session_id = f"totem-{int(time.time()*1000)}"

        # cria sessão no Redis
        get_or_create_session(company_id, session_id)

        # transições de estado
        self._transition(session_id, Event.PRESENCE_DETECTED)
        self._transition(session_id, Event.GREETING_DONE)

        # dispara UI
        publish(
            company_id=company_id,
            event="totem_activated",
            payload={
                "session_id": session_id,
                "message": "Olá! Como posso ajudar você hoje?"
            }
        )

        return session_id

    # =========================
    # INTERAÇÃO PRINCIPAL
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

        # estado → INTERACTION
        self._transition(session_id, Event.USER_MESSAGE)

        resposta, score, source = self._answer(company_id, pergunta)

        return self._finalize(
            company_id,
            session_id,
            pergunta,
            resposta,
            idioma,
            prefer_audio,
            started,
            score,
            source,
            profile or {},
        )

    # =========================
    # RESPOSTA (FAQ + CACHE + LLM)
    # =========================
    def _answer(self, company_id: str, pergunta: str):
        if not pergunta:
            return "Pode me dizer o que você procura?", 1.0, "system"

        climate_answer = answer_climate(company_id, pergunta)
        if climate_answer:
            return climate_answer

        cache_key = f"{company_id}:{normalize(pergunta)}"
        cached = cache_get(cache_key)

        if cached:
            return cached, 1.0, "cache"

        local_answer, local_score, local_source = answer_from_company_context(company_id, pergunta)

        if local_answer and local_score >= 0.35:
            answer = local_answer.strip()
            cache_set(cache_key, answer)
            return answer, local_score, local_source

        faq_answer, score = self.faq.search(pergunta, None)

        if faq_answer and score >= 0.65:
            answer = faq_answer.strip()
            cache_set(cache_key, answer)
            return answer, score, "faq"

        return self._llm_answer(company_id, pergunta), 0.55, "llm"

    # =========================
    # LLM
    # =========================
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
                    {"role": "system", "content": "Assistente de totem, objetivo e direto."},
                    {"role": "user", "content": pergunta},
                ],
                temperature=0.2,
                max_tokens=200,
            )

            return response.choices[0].message.content or ""

        except Exception:
            return "Não consegui responder agora."

    # =========================
    # FINALIZAÇÃO (RESPOSTA + RECOMMENDER + METRICS)
    # =========================
    def _finalize(
        self,
        company_id,
        session_id,
        pergunta,
        resposta,
        idioma,
        prefer_audio,
        started,
        score,
        source,
        profile,
    ):
        # salva histórico
        add_turn(session_id, pergunta, resposta)

        # treino async
        try:
            log_training_task.delay(session_id, pergunta, resposta, score)
        except Exception:
            pass

        # estado → RECOMMENDATION
        self._transition(session_id, Event.ANSWER_READY)

        # RECOMMENDER REAL
        campaigns = get_active_campaigns(company_id)

        recommendations = recommend_actions(
            profile,
            campaigns,
            intent=None,
        )

        # áudio
        audio_path = None
        if prefer_audio:
            audio_path, *_ = gerar_audio(resposta, idioma)

        latency = round(time.perf_counter() - started, 3)

        metric = {
            "source": source,
            "latency": latency,
        }

        # métricas locais
        self.metrics.save({
            "event": "interaction",
            "company_id": company_id,
            "session_id": session_id,
            "question": pergunta,
            "response": resposta,
            "latency": latency,
        })

        # evento realtime
        publish(
            company_id=company_id,
            event="interaction_completed",
            payload={
                "session_id": session_id,
                "response": resposta,
                "recommendations": recommendations,
            }
        )

        return resposta, recommendations, audio_path, metric, idioma
