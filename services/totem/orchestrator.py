from datetime import datetime
import time

from services.totem.language import detect_language
from services.totem.tts import gerar_audio
from services.totem.metrics import MetricsLogger
from services.llm_gateway_openai import chatgpt_generate
from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions
from recommender.scoring import infer_intent
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
        turn: int = 0,
        input_mode: str = "text",
        stt_provider: str | None = None,
        stt_latency_s: float | None = None,
        message_id: str | None = None,
    ):
        interaction_start = datetime.now()
        timestamp_iso = interaction_start.isoformat(timespec="seconds")
        idioma = detect_language(pergunta)
        data_hora = interaction_start.strftime("%d/%m/%Y (%A), %H:%M")

        # 1) marketing ativo
        active_campaigns = get_active_campaigns(company_id)

        # 2) intenção (NLP leve)
        intent = infer_intent(pergunta)

        # 3) recomendação por scoring (nível 1)
        recs = recommend_actions(profile, active_campaigns, intent=intent)

        # 4) prompt final para ChatGPT
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
 
        # 5) TTS
        audio_path = None
        voice_source = None
        hf_status = None
        hf_err = None
        tts_latency = None
        total_audio_latency = None

        if prefer_audio:
            audio_t0 = time.perf_counter()
            try:
                audio_path, voice_source, hf_status, hf_err, tts_latency = gerar_audio(
                    resposta, idioma, hugging_key=self.hugging_key
                )
            except Exception as e:
                hf_err = f"{type(e).__name__}: {e}"
                audio_t1 = time.perf_counter()
                total_audio_latency = round((audio_t1 - audio_t0), 3)

        # 6) métricas
        metric = {
            "timestamp": timestamp_iso,
            "company_id": company_id,
            "session_id": session_id,

            # contexto da interação
            "turn_index": turn,
            "input_mode": input_mode,
            "message_id": message_id,
            "intent": intent,

            # pergunta/resposta
            "question": pergunta,
            "response": resposta,

            # idioma
            "language_detected": idioma,
            "language_name": IDIOMAS.get(idioma, "Português"),

            # perfil e marketing
            "profile": profile,
            "campaigns_active": [
                (c.get("id") or c.get("campaign_id") or c.get("code"))
                for c in active_campaigns
                if (c.get("id") or c.get("campaign_id") or c.get("code"))
            ],
            "active_campaigns_count": len(active_campaigns),

            # recomendação estruturada
            "recommendations": recs,
            "recommendations_top": recs.get("top_actions"),

            # áudio/STT
            "stt_provider": stt_provider,
            "stt_latency_s": stt_latency_s,
            "voice_source": voice_source,
            "audio_file": audio_path,

            # latências
            "gen_latency_s": gen_latency,
            "tts_latency_s": tts_latency,
            "total_audio_time_s": total_audio_latency,

            # status externos
            "hf_status_code": hf_status,
            "hf_error": hf_err,
        }
        
        try:
            self.metrics.save(metric)
            self.metrics.build_report()
        except Exception as e:
            metric["metrics_error"] = f"{type(e).__name__}: {e}"

        return resposta, recs, audio_path, metric, idioma