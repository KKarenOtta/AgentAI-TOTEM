from __future__ import annotations

import os
import time
import logging
from typing import Tuple, Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("llm")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_S = float(os.getenv("OPENAI_TIMEOUT_S", "45"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "45"))

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
OPENROUTER_TIMEOUT_S = float(os.getenv("OPENROUTER_TIMEOUT_S", "45"))

LLM_FALLBACK_ORDER = os.getenv("LLM_FALLBACK_ORDER", "openai,gemini,openrouter")

# Resposta final quando nenhum provedor funcionar
DEMO_FALLBACK_TEXT = os.getenv(
    "LLM_DEMO_FALLBACK_TEXT",
    "[DEMO/OFFLINE] No momento não consigo acessar o modelo de IA.\n\n"
    "Ainda assim, posso te ajudar com recomendações baseadas nas campanhas ativas e no perfil.\n"
    "Toque em “Quero essa oferta” para gerar um QR."
)

# =========================
# Clients
# =========================
_openai_client = None
_gemini_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não definido no ambiente (.env).")

    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("Pacote 'openai' não instalado. Instale: pip install openai") from e

    _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_gemini_client():
    """
    Usa o SDK oficial google-genai.
    pip install google-genai
    """
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não definido no ambiente (.env).")

    try:
        from google import genai  # google-genai
    except Exception as e:
        raise RuntimeError("Pacote 'google-genai' não instalado. Instale: pip install google-genai") from e

    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# =========================
# Providers
# =========================
def _generate_openai(prompt: str, model: Optional[str] = None) -> Tuple[str, float]:
    client = _get_openai_client()
    model = model or OPENAI_MODEL
    t0 = time.perf_counter()

    # 1) Responses API (preferida)
    try:
        resp = client.responses.create(
            model=model,
            input=prompt,
            timeout=OPENAI_TIMEOUT_S,
        )
        text = getattr(resp, "output_text", None) or str(resp)
        return text.strip(), round(time.perf_counter() - t0, 3)
    except Exception as e_resp:
        logger.warning("OpenAI Responses falhou, tentando chat.completions: %s", e_resp)

    # 2) Chat Completions (fallback)
    cc = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout=OPENAI_TIMEOUT_S,
    )
    text = cc.choices[0].message.content or ""
    return text.strip(), round(time.perf_counter() - t0, 3)


def _generate_gemini(prompt: str, model: Optional[str] = None) -> Tuple[str, float]:
    """
    Gemini via google-genai (Text).
    """
    client = _get_gemini_client()
    model = model or GEMINI_MODEL
    t0 = time.perf_counter()

    # google-genai: client.models.generate_content
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
    )

    text = getattr(resp, "text", None)
    if not text:
        text = str(resp)

    return text.strip(), round(time.perf_counter() - t0, 3)


def _generate_openrouter(prompt: str, model: Optional[str] = None) -> Tuple[str, float]:
    """
    OpenRouter é compatível com o SDK OpenAI (base_url).
    pip install openai
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY não definido no ambiente (.env).")

    try:
        from openai import OpenAI
    except Exception as e:
        raise RuntimeError("Pacote 'openai' não instalado. Instale: pip install openai") from e

    model = model or OPENROUTER_MODEL
    t0 = time.perf_counter()

    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    # OpenRouter funciona bem com chat.completions
    cc = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout=OPENROUTER_TIMEOUT_S,
        extra_headers={
            # opcionais (bom para rate limit / identificação)
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Totem I.A.Gora"),
        }
    )
    text = cc.choices[0].message.content or ""
    return text.strip(), round(time.perf_counter() - t0, 3)


# =========================
# Orchestrator-facing function
# =========================
def chatgpt_generate(
    prompt: str,
    model: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Tuple[str, float]:
    """
    - Faz fallback: OpenAI -> Gemini -> OpenRouter -> DEMO
    - Se 'meta' for passado (dict), preenche:
        meta["llm_provider_used"]
        meta["llm_fallback_chain"]
        meta["llm_error"]
    """
    chain = []
    last_err = None

    order = [x.strip().lower() for x in LLM_FALLBACK_ORDER.split(",") if x.strip()]
    if not order:
        order = ["openai", "gemini", "openrouter"]

    # tenta cada provedor
    for provider in order:
        try:
            if provider == "openai":
                text, lat = _generate_openai(prompt, model=model)
                chain.append("openai:ok")
                if meta is not None:
                    meta["llm_provider_used"] = "openai"
                    meta["llm_fallback_chain"] = chain
                    meta["llm_error"] = None
                return text, lat

            if provider == "gemini":
                text, lat = _generate_gemini(prompt, model=None)  # usa GEMINI_MODEL
                chain.append("gemini:ok")
                if meta is not None:
                    meta["llm_provider_used"] = "gemini"
                    meta["llm_fallback_chain"] = chain
                    meta["llm_error"] = None
                return text, lat

            if provider == "openrouter":
                text, lat = _generate_openrouter(prompt, model=None)  # usa OPENROUTER_MODEL
                chain.append("openrouter:ok")
                if meta is not None:
                    meta["llm_provider_used"] = "openrouter"
                    meta["llm_fallback_chain"] = chain
                    meta["llm_error"] = None
                return text, lat

            # provider desconhecido
            chain.append(f"{provider}:skipped_unknown")

        except Exception as e:
            last_err = e
            # reduz log verboso, mas registra cadeia
            chain.append(f"{provider}:fail:{type(e).__name__}")
            logger.warning("LLM provider '%s' falhou: %s", provider, e)

    # nenhum funcionou -> DEMO
    if meta is not None:
        meta["llm_provider_used"] = "demo"
        meta["llm_fallback_chain"] = chain
        meta["llm_error"] = f"{type(last_err).__name__}: {last_err}" if last_err else "unknown_error"

    # latency: soma aproximada não vale; retorna tempo total do fallback
    # (aqui só retorna 0.0 para não impactar relatórios; você pode mudar se quiser)
    return DEMO_FALLBACK_TEXT, 0.0