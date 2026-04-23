from __future__ import annotations

from datetime import datetime
import time

from marketing.campaigns import get_active_campaigns
from recommender.rules import recommend_actions
from recommender.scoring import infer_intent

from services.llm_gateway_openai import chatgpt_generate

from services.totem.language import detect_language
from services.totem.metrics import MetricsLogger
from services.totem.tts import gerar_audio
from services.totem.company_context import load_company_context


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
        start = datetime.now()
        idioma = detect_language(pergunta or "")

        context = load_company_context(company_id)
        active_campaigns = get_active_campaigns(company_id)
        intent = infer_intent(pergunta or "")

        recs = recommend_actions(profile, active_campaigns, intent=intent) or {}

        # =========================
        # 1. BUSCA LOCAL FORTE
        # =========================
        base_answer, source = self._search_local_context(pergunta, context)

        # =========================
        # 2. FALLBACK IA (SE NECESSÁRIO)
        # =========================
        resposta_final = base_answer

        if source == "none":
            resposta_final = self._generate_with_ai(pergunta, context, active_campaigns)

        elif source == "partial":
            complemento = self._generate_with_ai(pergunta, context, active_campaigns)
            resposta_final = f"{base_answer}\n\n{complemento}"

        # =========================
        # 3. FINALIZAÇÃO PADRÃO
        # =========================
        resposta_final += "\n\nPosso te ajudar com mais alguma coisa?"

        # =========================
        # 4. TTS
        # =========================
        audio_path = None
        if prefer_audio:
            audio_path, *_ = gerar_audio(resposta_final, idioma)

        return resposta_final, recs, audio_path, {}, idioma

    # =====================================================
    # BUSCA LOCAL INTELIGENTE
    # =====================================================
    def _search_local_context(self, pergunta: str, context: dict):
        if not pergunta or not context:
            return "", "none"

        pergunta = pergunta.lower()

        score = 0
        resposta = ""

        # -------------------------
        # FAQ
        # -------------------------
        for faq in context.get("faq", []):
            q = faq.get("question", "").lower()
            if any(word in pergunta for word in q.split()):
                return faq.get("answer", ""), "exact"

        # -------------------------
        # LOCALIZAÇÃO
        # -------------------------
        if any(k in pergunta for k in ["onde", "local", "fica", "localização"]):
            loc = context.get("location", {})
            if loc:
                resposta += f"O local está em {loc.get('address', 'endereço não informado')}.\n"
                score += 1

        # -------------------------
        # ATRAÇÕES
        # -------------------------
        if any(k in pergunta for k in ["atração", "evento", "o que tem", "lazer"]):
            atracoes = context.get("attractions", [])
            if atracoes:
                lista = "\n".join([f"• {a}" for a in atracoes])
                resposta += f"Aqui você encontra:\n{lista}\n"
                score += 1

        # -------------------------
        # LOJAS
        # -------------------------
        if any(k in pergunta for k in ["loja", "comprar", "shopping"]):
            lojas = context.get("stores", [])
            if lojas:
                lista = "\n".join([f"• {l}" for l in lojas[:5]])
                resposta += f"Algumas lojas disponíveis:\n{lista}\n"
                score += 1

        # -------------------------
        # SERVIÇOS
        # -------------------------
        if any(k in pergunta for k in ["banheiro", "serviço", "atendimento"]):
            servicos = context.get("services", [])
            if servicos:
                lista = "\n".join([f"• {s}" for s in servicos])
                resposta += f"Serviços disponíveis:\n{lista}\n"
                score += 1

        # -------------------------
        # DESCRIÇÃO GERAL
        # -------------------------
        if score == 0:
            return context.get("description", ""), "partial"

        return resposta.strip(), "exact"

    # =====================================================
    # IA COMPLEMENTAR
    # =====================================================
    def _generate_with_ai(self, pergunta: str, context: dict, campaigns: list):
        prompt = f"""
Você é um assistente de um totem físico em um ambiente comercial.

CONTEXTO DO LOCAL:
{context}

PERGUNTA DO USUÁRIO:
{pergunta}

REGRAS:
- Use o contexto acima
- Não invente informações
- Seja direto e útil
- Se não souber algo específico, seja transparente
- Sugira o que o usuário pode fazer no local
""".strip()

        try:
            resposta, _ = chatgpt_generate(prompt)
            return resposta
        except Exception:
            return "Posso te ajudar com informações do local e ofertas disponíveis."
