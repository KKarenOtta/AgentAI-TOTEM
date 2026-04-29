import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text

load_dotenv("/home/ubuntu/totem.env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
engine = create_engine(os.getenv("DATABASE_URL"))


def gerar_embedding(texto: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )
    return response.data[0].embedding


def montar_documentos(company_id, empresa):
    docs = []

    docs.append({
        "titulo": f"{company_id} - descrição",
        "conteudo": f"{empresa.get('name', '')}. {empresa.get('description', '')}",
        "fonte": "company_contexts.json"
    })

    location = empresa.get("location", {})
    docs.append({
        "titulo": f"{company_id} - localização",
        "conteudo": f"Endereço: {location.get('address', '')}. Referência: {location.get('reference', '')}.",
        "fonte": "company_contexts.json"
    })

    hours = empresa.get("hours", {})
    docs.append({
        "titulo": f"{company_id} - horários",
        "conteudo": f"Horário de segunda a sábado: {hours.get('monday_to_saturday', '')}. Domingo: {hours.get('sunday', '')}. Feriados: {hours.get('holidays', '')}.",
        "fonte": "company_contexts.json"
    })

    contacts = empresa.get("contacts", {})
    docs.append({
        "titulo": f"{company_id} - contatos",
        "conteudo": f"Telefone: {contacts.get('phone', '')}. Email: {contacts.get('email', '')}. Site: {contacts.get('site', '')}.",
        "fonte": "company_contexts.json"
    })

    for service in empresa.get("services", []):
        docs.append({
            "titulo": f"{company_id} - serviço - {service.get('name', '')}",
            "conteudo": f"Serviço: {service.get('name', '')}. Categoria: {service.get('category', '')}. Zona: {service.get('zone', '')}. Referência: {service.get('reference', '')}. Tags: {', '.join(service.get('tags', []))}.",
            "fonte": "company_contexts.json"
        })

    for item in empresa.get("faq", []):
        docs.append({
            "titulo": f"{company_id} - FAQ - {item.get('question', '')}",
            "conteudo": f"Pergunta: {item.get('question', '')}. Resposta: {item.get('answer', '')}",
            "fonte": "company_contexts.json"
        })

    for policy in empresa.get("policies", []):
        docs.append({
            "titulo": f"{company_id} - política",
            "conteudo": policy,
            "fonte": "company_contexts.json"
        })

    return docs


with open("data/company_contexts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS base_conhecimento (
            id SERIAL PRIMARY KEY,
            company_id TEXT,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            fonte TEXT,
            embedding vector(1536)
        )
    """))

    conn.execute(text("DELETE FROM base_conhecimento"))

    total = 0

    for company_id, empresa in data.items():
        documentos = montar_documentos(company_id, empresa)

        for doc in documentos:
            embedding = gerar_embedding(doc["conteudo"])

            conn.execute(
                text("""
                    INSERT INTO base_conhecimento
                    (company_id, titulo, conteudo, fonte, embedding)
                    VALUES (:company_id, :titulo, :conteudo, :fonte, :embedding)
                """),
                {
                    "company_id": company_id,
                    "titulo": doc["titulo"],
                    "conteudo": doc["conteudo"],
                    "fonte": doc["fonte"],
                    "embedding": str(embedding)
                }
            )

            total += 1

print(f"Base vetorizada com sucesso. {total} documentos inseridos.")
