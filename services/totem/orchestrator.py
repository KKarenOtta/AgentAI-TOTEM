from datetime import datetime
import time

from services.totem.language import detect_language
from services.totem.tts import gerar_audio
from services.totem.metrics import MetricsLogger
from services.llm_gateway_openai import chatgpt_generate
from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions
from services.realtime.event_bus import publish

IDIOMAS = {"pt": "Português", "en": "Inglês", "es": "Espanhol"}


class TotemOrchestrator:
    def __init__(self, hugging_key: str | None = None):
        self.hugging_key = hugging_key
        self.metrics = MetricsLogger()

    def interact(
        self,
        company_id: str,
        session_id: str,
        pergunta: str,
        profile: dict | None,
        prefer_audio: bool = True,
    ):
        interaction_start = datetime.now()
        timestamp_iso = interaction_start.isoformat(timespec="seconds")

        idioma = detect_language(pergunta)
        data_hora = interaction_start.strftime("%d/%m/%Y (%A), %H:%M")

        # 1) marketing ativo
        active_campaigns = get_active_campaigns(company_id)

        # 2) recomendação (regras/ML)
        recs = recommend_actions(profile, active_campaigns)

        # 3) prompt final para ChatGPT
        prompt = f"""
            Agora são {data_hora}.
            Responda em {IDIOMAS.get(idioma, "Português")}.
            Você é um assistente de totem de autoatendimento (rápido, claro, educado).
            Use o perfil e as campanhas ativas para personalizar a conversa.

            PERGUNTA DO USUÁRIO:
            {pergunta}

            PERFIL (informado pelo totem):
            {profile}

            CAMPANHAS ATIVAS (marketing):
            {active_campaigns}

            RECOMENDAÇÕES (estruturadas):
            {recs}

            REGRAS DE RESPOSTA:
            - Seja direto e amigável.
            - Faça no máximo 1 pergunta de clarificação (se necessário).
            - Inclua um "próximo passo" para o usuário.
        """

        resposta, gen_latency = chatgpt_generate(prompt)

        # 4) TTS
        audio_path = None
        voice_source = None
        hf_status = None
        hf_err = None
        tts_latency = None
        total_audio_latency = None

        if prefer_audio:
            audio_t0 = time.perf_counter()
            audio_path, voice_source, hf_status, hf_err, tts_latency = gerar_audio(
                resposta, idioma, hugging_key=self.hugging_key
            )
            audio_t1 = time.perf_counter()
            total_audio_latency = round((audio_t1 - audio_t0), 3)

        # 5) métricas
        metric = {
            "timestamp": timestamp_iso,
            "company_id": company_id,
            "session_id": session_id,
            "question": pergunta,
            "response": resposta,
            "language_detected": idioma,
            "language_name": IDIOMAS.get(idioma, "Português"),
            "profile": profile,
            "active_campaigns_count": len(active_campaigns),
            "recommendations": recs,
            "voice_source": voice_source,
            "audio_file": audio_path,
            "gen_latency_s": gen_latency,
            "tts_latency_s": tts_latency,
            "total_audio_time_s": total_audio_latency,
            "hf_status_code": hf_status,
            "hf_error": hf_err,
        }

        self.metrics.save(metric)
        self.metrics.build_report()

        # 6) evento realtime para página /totem/live
        try:
            publish(company_id, {
                "type": "totem_interaction",
                "timestamp": timestamp_iso,
                "company_id": company_id,
                "session_id": session_id,
                "profile": profile,
                "question": pergunta,
                "response": resposta,
                "recommendations": recs,
                "latency": {"gen": gen_latency, "tts": tts_latency},
                "audio_file": audio_path,
                "voice_source": voice_source,
            })
        except Exception:
            pass

        return resposta, recs, audio_path, metric, idioma