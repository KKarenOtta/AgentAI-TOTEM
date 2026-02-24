import os, time
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chatgpt_generate(prompt: str, model: str = "gpt-4.1-mini"):
    """
    Retorna (text, latency_s).
    Ajuste o model conforme seu plano/custo.
    """
    t0 = time.perf_counter()

    resp = client.responses.create(
        model=model,
        input=prompt,
    )

    # Texto final (Responses API pode retornar múltiplos outputs)
    text = ""
    for o in resp.output:
        if o.type == "message":
            for c in o.content:
                if c.type == "output_text":
                    text += c.text

    t1 = time.perf_counter()
    return text.strip(), round((t1 - t0), 3)