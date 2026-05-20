from __future__ import annotations

import os
from openai import OpenAI
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv("/home/ubuntu/totem.env")

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("DEBUG DATABASE_URL =", DATABASE_URL)

engine = create_engine(DATABASE_URL)
client = OpenAI(api_key=OPENAI_API_KEY)


def gerar_embedding(texto: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texto,
    )
    return response.data[0].embedding


def search_knowledge(
    company_id: str,
    query: str,
    top_k: int = 5,
):
    embedding = gerar_embedding(query)

    sql = text("""
        SELECT
            titulo,
            conteudo,
            fonte,
            1 - (embedding <=> CAST(:embedding AS vector)) AS score
        FROM base_conhecimento
        WHERE company_id = :company_id
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {
                "embedding": embedding,   # 👈 FIX PRINCIPAL
                "company_id": company_id,
                "top_k": top_k,
            },
        ).mappings().all()

    return [dict(r) for r in rows]

def synthesize_answer(question: str, chunks: list[dict]):
    if not chunks:
        return "Não encontrei informações na base de conhecimento."

    context = "\n\n---\n\n".join(
        f"TÍTULO: {c['titulo']}\nCONTEÚDO: {c['conteudo']}"
        for c in chunks
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um assistente de um sistema de informações (totem). "
                    "Responda SOMENTE com base no contexto fornecido. "
                    "Se a informação não estiver no contexto, diga que não encontrou dados. "
                    "Organize a resposta de forma clara e estruturada."
                )
            },
            {
                "role": "user",
                "content": f"""
PERGUNTA:
{question}

CONTEXTO:
{context}
"""
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content

def ask_rag(company_id: str, question: str):
    chunks = search_knowledge(company_id, question)
    return synthesize_answer(question, chunks)
