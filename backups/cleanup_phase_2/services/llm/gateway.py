from __future__ import annotations


def generate_text(message: str, system_prompt: str | None = None) -> str:
    try:
        from services.llm_gateway_openai import generate_reply  # type: ignore
        return generate_reply(message=message, system_prompt=system_prompt)
    except Exception:
        return "Posso ajudar com informações, ofertas, produtos e suporte."
