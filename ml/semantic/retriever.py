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
            1 - (embedding <=> :embedding::vector) AS score
        FROM base_conhecimento
        WHERE company_id = :company_id
        ORDER BY embedding <=> :embedding::vector
        LIMIT :top_k
    """)

    with engine.begin() as conn:
        rows = conn.execute(
            sql,
            {
                "embedding": str(embedding),
                "company_id": company_id,
                "top_k": top_k,
            },
        ).mappings().all()

    return [dict(r) for r in rows]
