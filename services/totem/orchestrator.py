from __future__ import annotations

from datetime import datetime
import time

from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions
from recommender.scoring import infer_intent
from services.llm_gateway_openai import chatgpt_generate
from services.realtime.event_bus import publish
from services.totem.language import detect_language
from services.totem.metrics import MetricsLogger
from services.totem.qr import generate_campaign_qr
from services.totem.tts import gerar_audio


IDIOMAS = {"pt": "Português", "en": "Inglês", "es": "Espanhol"}


class TotemOrchestrator:
    def __init__(self, hugging_key: str | None = None):
        self.hugging_key = hugging_key
        self.metrics = MetricsLogger()

    @staticmethod
    def _normalize_discount_label(action: dict) -> str | None:
        discount_type = action.get("discount_type")
        discount_value = action.get("discount_value")

        if discount_value in (None, "", 0, 0.0):
            return None

        try:
            numeric_value = float(discount_value)
        except Exception:
            return None

        if discount_type == "percent":
            return f"{int(numeric_value)}% OFF"

        if discount_type == "fixed":
            return f"R$ {numeric_value:.2f} OFF"

        return None

    def _enrich_recommendations(
        self,
        *,
        recs: dict | None,
        company_id: str,
        session_id: str,
        turn: int,
    ) -> dict:
        if not isinstance(recs, dict):
            return {"top_actions": []}

        top_actions = recs.get("top_actions")
        if not isinstance(top_actions, list):
            recs["top_actions"] = []
            return recs

        enriched = []
        for action in top_actions:
            if not isinstance(action, dict):
                continue

            campaign_id = action.get("campaign_id") or action.get("id") or action.get("code")
            coupon_code = action.get("coupon_code") or campaign_id

            qr_payload = {
                "company_id": company_id,
                "campaign_id": campaign_id,
                "coupon_code": coupon_code,
                "session_id": session_id,
                "turn_index": turn,
                "ts": int(time.time()),
            }

            item = dict(action)
            item["discount_label"] = self._normalize_discount_label(item)
            item["qr_code_url"] = generate_campaign_qr(qr_payload)

            if not item.get("cta_label"):
                item["cta_label"] = "Quero meu desconto"

            enriched.append(item)

        recs["top_actions"] = enriched
        return recs

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
        idioma = detect_language(pergunta or "")
        data_hora = interaction_start.strftime("%d/%m/%Y (%A), %H:%M")

        active_campaigns = get_active_campaigns(company_id)

        campaign_ids = [
            (c.get("id") or c.get("campaign_id") or c.get("code"))
            for c in (active_campaigns or [])
            if (c.get("id") or c.get("campaign_id") or c.get("code"))
        ]

        intent = infer_intent(pergunta or "")
        recs = recommend_actions(profile, active_campaigns, intent=intent) or {}
        recs = self._enrich_recommendations(
            recs=recs,
            company_id=company_id,
            session_id=session_id,
            turn=turn,
        )

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
- Inclua um próximo passo para o usuário.
""".strip()

        llm_meta: dict = {}
        resposta = ""
        gen_latency = None

        try:
            resposta, gen_latency = chatgpt_generate(prompt, meta=llm_meta)
        except Exception as e:
            llm_meta["llm_provider_used"] = "demo"
            llm_meta["llm_fallback_chain"] = llm_meta.get("llm_fallback_chain") or ["gateway:fail"]
            llm_meta["llm_error"] = f"{type(e).__name__}: {e}"
            gen_latency = None
            resposta = (
                "[DEMO/OFFLINE] No momento não consigo acessar o modelo de IA.\n\n"
                "Ainda assim posso te orientar com base nas campanhas e recomendações.\n"
                "Toque em “Quero essa oferta” para gerar um QR."
            )

        llm_provider_used = llm_meta.get("llm_provider_used")
        llm_fallback_chain = llm_meta.get("llm_fallback_chain")
        llm_error = llm_meta.get("llm_error")

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
                    resposta,
                    idioma,
                    hugging_key=self.hugging_key,
                )
                audio_t1 = time.perf_counter()
                total_audio_latency = round((audio_t1 - audio_t0), 3)
            except Exception as e:
                audio_t1 = time.perf_counter()
                total_audio_latency = round((audio_t1 - audio_t0), 3)
                hf_err = f"{type(e).__name__}: {e}"

        latency_total_s = (
            (gen_latency or 0.0) +
            (tts_latency or 0.0) +
            (stt_latency_s or 0.0)
        )

        metric = {
            "timestamp": timestamp_iso,
            "company_id": company_id,
            "session_id": session_id,
            "turn_index": turn,
            "input_mode": input_mode,
            "message_id": message_id,
            "intent": intent,
            "question": pergunta,
            "response": resposta,
            "language_detected": idioma,
            "language_name": IDIOMAS.get(idioma, "Português"),
            "profile": profile,
            "campaigns_active": campaign_ids,
            "active_campaigns_count": len(active_campaigns or []),
            "campaign_impressions": campaign_ids,
            "campaign_impressions_count": len(campaign_ids),
            "recommendations": recs,
            "recommendations_top": recs.get("top_actions") if isinstance(recs, dict) else None,
            "stt_provider": stt_provider,
            "stt_latency_s": stt_latency_s,
            "voice_source": voice_source,
            "audio_file": audio_path,
            "gen_latency_s": gen_latency,
            "tts_latency_s": tts_latency,
            "total_audio_time_s": total_audio_latency,
            "latency_llm_s": gen_latency,
            "latency_tts_s": tts_latency,
            "latency_total_s": latency_total_s,
            "hf_status_code": hf_status,
            "hf_error": hf_err,
            "llm_provider_used": llm_provider_used,
            "llm_fallback_chain": llm_fallback_chain,
            "llm_error": llm_error,
        }

        impression_event = {
            "event": "campaign_impression",
            "timestamp": timestamp_iso,
            "company_id": company_id,
            "session_id": session_id,
            "turn_index": turn,
            "campaign_ids": campaign_ids,
            "campaign_count": len(campaign_ids),
            "intent": intent,
            "language_detected": idioma,
            "llm_provider_used": llm_provider_used,
        }

        live_event = {
            "type": "totem_interaction",
            "event": "totem_interaction",
            "timestamp": timestamp_iso,
            "company_id": company_id,
            "session_id": session_id,
            "turn_index": turn,
            "input_mode": input_mode,
            "message_id": message_id,
            "intent": intent,
            "language": idioma,
            "question": pergunta,
            "response": resposta,
            "profile": profile,
            "recommendations": recs,
            "recommendations_top": recs.get("top_actions") if isinstance(recs, dict) else [],
            "audio_file": audio_path,
            "voice_source": voice_source,
            "latency": {
                "stt": stt_latency_s,
                "llm": gen_latency,
                "tts": tts_latency,
                "total": latency_total_s,
            },
            "campaign_ids": campaign_ids,
            "llm_provider_used": llm_provider_used,
            "status": {
                "hf_status_code": hf_status,
                "hf_error": hf_err,
                "llm_error": llm_error,
            },
        }

        live_impression_event = {
            "type": "campaign_impression",
            "event": "campaign_impression",
            "timestamp": timestamp_iso,
            "company_id": company_id,
            "session_id": session_id,
            "turn_index": turn,
            "campaign_ids": campaign_ids,
            "campaign_count": len(campaign_ids),
            "intent": intent,
            "language": idioma,
        }

        try:
            self.metrics.save(metric)
            self.metrics.save(impression_event)
            self.metrics.build_report()
        except Exception as e:
            metric["metrics_error"] = f"{type(e).__name__}: {e}"

        try:
            publish(company_id=company_id, event="totem_interaction", payload=live_event)
            publish(company_id=company_id, event="campaign_impression", payload=live_impression_event)
        except Exception as e:
            metric["publish_error"] = f"{type(e).__name__}: {e}"

        return resposta, recs, audio_path, metric, idioma
