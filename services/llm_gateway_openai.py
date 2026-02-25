import os, time
from openai import OpenAI
from openai import RateLimitError, APIError, APIConnectionError, AuthenticationError

def _get_client() -> OpenAI | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)

def chatgpt_generate(prompt: str, model: str = "gpt-4.1-mini"):
    t0 = time.perf_counter()

    client = _get_client()
    if client is None:
        t1 = time.perf_counter()
        return ("[DEMO] OPENAI_API_KEY não configurada no ambiente."), round((t1 - t0), 3)

    try:
        resp = client.responses.create(model=model, input=prompt)

        text = ""
        for o in resp.output:
            if o.type == "message":
                for c in o.content:
                    if c.type == "output_text":
                        text += c.text

        t1 = time.perf_counter()
        return text.strip(), round((t1 - t0), 3)

    except AuthenticationError:
        t1 = time.perf_counter()
        return ("[DEMO] Chave OpenAI inválida/sem permissão (401)."), round((t1 - t0), 3)

    except RateLimitError:
        t1 = time.perf_counter()
        return ("[DEMO] Sem quota/limite (429)."), round((t1 - t0), 3)

    except (APIError, APIConnectionError):
        t1 = time.perf_counter()
        return ("[DEMO] Falha temporária na OpenAI/rede."), round((t1 - t0), 3)