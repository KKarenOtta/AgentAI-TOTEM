from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

from infra.async_tasks.tasks import log_training_task

from ml.semantic.faq_engine import FAQEngine
from ml.semantic.cache import get as cache_get, set as cache_set

from core.totem.language import detect_language
from core.totem.metrics import MetricsLogger
from core.totem.tts import gerar_audio
from core.totem.session_store import add_turn, get_context, get_session, set_last_intent
from core.totem.qr import generate_qr_from_text

from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions

MAP_URL = "https://zoologico.com.br/sobre/mapa-zoo-sao-paulo"

YES_WORDS = {"sim", "s", "claro", "quero", "pode", "nova pergunta"}
NO_WORDS = {"não", "nao", "n", "obrigado", "obrigada", "encerrar", "finalizar"}

HANDOFF_DIR = Path("data/device_handoffs")


def normalize(text: str) -> str:
    return (text or "").strip().lower()


class TotemOrchestrator:
    def __init__(self):
        self.metrics = MetricsLogger()
        self.faq = FAQEngine()

    def interact(self, company_id, session_id, pergunta, profile, prefer_audio=True, **kwargs):
        started = time.perf_counter()
        pergunta = (pergunta or "").strip()
        idioma = detect_language(pergunta)

        session = get_session(session_id) or {}
        last_intent = session.get("last_intent") if isinstance(session, dict) else None

        if last_intent == "awaiting_more_help":
            resposta, source = self._handle_more_help(company_id, session_id, normalize(pergunta))
            return self._finalize(company_id, session_id, pergunta, resposta, idioma, prefer_audio, started, 1.0, source, profile)

        resposta, score, source = self._answer(company_id, session_id, pergunta)

        set_last_intent(session_id, "awaiting_more_help")
        resposta = f"{resposta}\n\nPosso ajudar em algo mais?"

        return self._finalize(company_id, session_id, pergunta, resposta, idioma, prefer_audio, started, score, source, profile)

    def _answer(self, company_id, session_id, pergunta):
        cache_key = f"{company_id}:{normalize(pergunta)}"

        cached = cache_get(cache_key)
        if cached:
            return cached, 1.0, "cache"

        faq_answer, score = self.faq.search(pergunta, None)

        if faq_answer and score >= 0.7:
            cache_set(cache_key, faq_answer)
            return faq_answer, score, "faq"

        return self._llm_fallback(pergunta), 0.5, "llm"

    def _llm_fallback(self, pergunta):
        return f"Para mais detalhes, consulte o mapa oficial: {MAP_URL}"

    def _handle_more_help(self, company_id, session_id, resposta_usuario):
        if resposta_usuario in YES_WORDS:
            set_last_intent(session_id, None)
            return "Claro. Pode perguntar.", "continue"

        if resposta_usuario in NO_WORDS:
            set_last_intent(session_id, None)
            link = self._save_handoff(company_id, session_id)
            return "Obrigado pela visita. Continue no seu celular.", "handoff"

        return "Responda sim ou não.", "awaiting"

    def _save_handoff(self, company_id, session_id):
        base_url = os.getenv("TOTEM_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        link = f"{base_url}/device/{company_id}/{session_id}"

        HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
        (HANDOFF_DIR / f"{session_id}.json").write_text(json.dumps({"link": link}), encoding="utf-8")

        return link

    def _finalize(self, company_id, session_id, pergunta, resposta, idioma, prefer_audio, started, score, source, profile):
        add_turn(session_id, pergunta, resposta)

        try:
            log_training_task.delay(session_id, pergunta, resposta, score)
        except Exception:
            pass

        # =========================
        # RECOMENDAÇÃO REAL
        # =========================
        campaigns = get_active_campaigns(company_id)

        recommendations = recommend_actions(
            profile=profile or {},
            campaigns=campaigns,
            intent=normalize(pergunta)
        )

        # =========================
        # AUDIO
        # =========================
        audio_path = None
        audio_provider = None

        if prefer_audio:
            audio_path, audio_provider, *_ = gerar_audio(resposta, idioma)

        metric = {
            "source": source,
            "score": score,
            "latency": time.perf_counter() - started,
            "recommendations_count": len(recommendations),
        }

        return resposta, recommendations, audio_path, metric, idioma
