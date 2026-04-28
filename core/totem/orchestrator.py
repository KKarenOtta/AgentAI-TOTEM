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
from core.totem.session_store import add_turn
from core.totem.tts import gerar_audio

DEFAULT_SITE = "https://zoologico.com.br"
DEFAULT_MAP_URL = "https://zoologico.com.br/sobre/mapa-zoo-sao-paulo"


def normalize(text: str) -> str:
    return (text or "").strip().lower()


class TotemOrchestrator:
    def __init__(self) -> None:
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    # NOVO: controle central de presença
    def handle_presence_event(self, company_id: str, payload: dict):

        if not payload.get("present"):
            return

        session_id = f"totem-{int(time.time()*1000)}"

        publish(
            company_id=company_id,
            event="totem_activated",
            payload={
                "session_id": session_id,
                "message": "Olá! Como posso ajudar você hoje?"
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

    def _answer(self, company_id: str, pergunta: str):
        if not pergunta:
            return "Pode me dizer o que você procura?", 1.0, "system"

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
        add_turn(session_id, pergunta, resposta)

        try:
            log_training_task.delay(session_id, pergunta, resposta, score)
        except Exception:
            pass

        audio_path = None

        if prefer_audio:
            audio_path, *_ = gerar_audio(resposta, idioma)

        metric = {
            "source": source,
            "latency": round(time.perf_counter() - started, 3),
        }

        self.metrics.save({
            "event": "interaction",
            "company_id": company_id,
            "session_id": session_id,
            "question": pergunta,
            "response": resposta,
            "latency": metric["latency"],
        })

        return resposta, {"top_actions": []}, audio_path, metric, idioma
