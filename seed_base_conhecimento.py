import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text


ROOT_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definida.")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY não definida.")

client = OpenAI(api_key=OPENAI_API_KEY)
engine = create_engine(DATABASE_URL)


def gerar_embedding(conteudo: str):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=conteudo,
    )
    return response.data[0].embedding


def lista_para_texto(lista):
    if not lista:
        return "não informado"
    if isinstance(lista, list):
        return ", ".join(lista)
    return str(lista)


def montar_documentos_company_contexts(data: dict):
    documentos = []

    for company_id, empresa in data.items():
        nome = empresa.get("name", "")
        business_type = empresa.get("business_type", "")
        descricao = empresa.get("description", "")

        location = empresa.get("location", {})
        hours = empresa.get("hours", {})
        contacts = empresa.get("contacts", {})
        services = empresa.get("services", [])
        stores = empresa.get("stores", [])
        attractions = empresa.get("attractions", [])
        policies = empresa.get("policies", [])

        documentos.append({
            "company_id": company_id,
            "titulo": f"{company_id} - visão geral do zoológico",
            "conteudo": (
                f"{nome}. Tipo de negócio: {business_type}. "
                f"Descrição: {descricao}. "
                f"O local possui atrações, área de visitação, lojas, praça de alimentação, "
                f"serviços, banheiros e atendimento ao visitante. "
                f"Este texto responde perguntas sobre estrutura geral, funcionamento do local, "
                f"o que existe no zoológico, facilidades disponíveis e atendimento ao público."
            ),
            "fonte": "company_contexts.json",
        })

        documentos.append({
            "company_id": company_id,
            "titulo": f"{company_id} - endereço localização e como chegar",
            "conteudo": (
                f"O endereço completo do zoológico é {location.get('address', '')}. "
                f"A referência de localização é: {location.get('reference', '')}. "
                f"O link do mapa é {location.get('map_url', '')}. "
                f"O mapa oficial é {location.get('official_map_url', '')}. "
                f"Este texto responde perguntas sobre endereço, localização, onde fica, "
                f"como chegar, ponto de referência, referência próxima e mapa."
            ),
            "fonte": "company_contexts.json",
        })

        documentos.append({
            "company_id": company_id,
            "titulo": f"{company_id} - horários de funcionamento",
            "conteudo": (
                f"O horário de funcionamento de segunda a sábado é {hours.get('monday_to_saturday', '')}. "
                f"O horário de funcionamento aos domingos é {hours.get('sunday', '')}. "
                f"Em feriados: {hours.get('holidays', '')}. "
                f"Se o visitante perguntar sobre sábado, domingo, dias de semana, entrada, "
                f"abertura, fechamento ou horário de visita, use estas informações."
            ),
            "fonte": "company_contexts.json",
        })

        documentos.append({
            "company_id": company_id,
            "titulo": f"{company_id} - contatos oficiais",
            "conteudo": (
                f"O telefone de contato é {contacts.get('phone', '')}. "
                f"O email de atendimento é {contacts.get('email', '')}. "
                f"O site oficial é {contacts.get('site', '')}. "
                f"Este texto responde perguntas sobre telefone, email, site, contato, "
                f"atendimento e como falar com o zoológico."
            ),
            "fonte": "company_contexts.json",
        })

        nomes_servicos = [s.get("name", "") for s in services]
        nomes_lojas = [s.get("name", "") for s in stores]
        nomes_atracoes = [a.get("name", "") for a in attractions]

        documentos.append({
            "company_id": company_id,
            "titulo": f"{company_id} - resumo de serviços lojas atrações e facilidades",
            "conteudo": (
                f"As principais facilidades do zoológico incluem serviços, lojas, atrações, "
                f"praça de alimentação e atendimento ao visitante. "
                f"Serviços disponíveis: {lista_para_texto(nomes_servicos)}. "
                f"Lojas e estabelecimentos comerciais: {lista_para_texto(nomes_lojas)}. "
                f"Atrações e pontos de interesse: {lista_para_texto(nomes_atracoes)}. "
                f"Este texto responde perguntas sobre estrutura completa, facilidades, "
                f"serviços ao visitante, alimentação, descanso, lojas, comércio, atrações "
                f"e preparo para receber o público."
            ),
            "fonte": "company_contexts.json",
        })

        for service in services:
            documentos.append({
                "company_id": company_id,
                "titulo": f"{company_id} - serviço - {service.get('name', '')}",
                "conteudo": (
                    f"O serviço {service.get('name', '')} está disponível no zoológico. "
                    f"Categoria do serviço: {service.get('category', '')}. "
                    f"Zona ou área: {service.get('zone', '')}. "
                    f"Referência de localização: {service.get('reference', '')}. "
                    f"Tags relacionadas: {lista_para_texto(service.get('tags', []))}. "
                    f"Este texto responde perguntas sobre serviço, atendimento, ajuda, "
                    f"banheiro, fraldário, informação, apoio ao visitante e estrutura."
                ),
                "fonte": "company_contexts.json",
            })

        for store in stores:
            documentos.append({
                "company_id": company_id,
                "titulo": f"{company_id} - loja - {store.get('name', '')}",
                "conteudo": (
                    f"A loja ou estabelecimento {store.get('name', '')} existe dentro do zoológico. "
                    f"Categoria: {store.get('category', '')}. "
                    f"Zona ou área interna: {store.get('zone', '')}. "
                    f"Referência de localização: {store.get('reference', '')}. "
                    f"Tags relacionadas: {lista_para_texto(store.get('tags', []))}. "
                    f"Este texto responde perguntas sobre lojas, comércio, estabelecimentos comerciais, "
                    f"lembranças, presentes, souvenirs, roupa, camiseta, brinquedo, alimentação, "
                    f"comida, lanche, café, restaurante e praça de alimentação."
                ),
                "fonte": "company_contexts.json",
            })

        for attraction in attractions:
            documentos.append({
                "company_id": company_id,
                "titulo": f"{company_id} - atração - {attraction.get('name', '')}",
                "conteudo": (
                    f"A atração {attraction.get('name', '')} faz parte do zoológico. "
                    f"Categoria da atração: {attraction.get('category', '')}. "
                    f"Referência de localização: {attraction.get('reference', '')}. "
                    f"Tags relacionadas: {lista_para_texto(attraction.get('tags', []))}. "
                    f"Este texto responde perguntas sobre atrações, animais, visitação, "
                    f"áreas do zoológico, espécies, pontos de interesse, leões, felinos, "
                    f"pinguins, área kids, alimentação e lazer."
                ),
                "fonte": "company_contexts.json",
            })

        for item in empresa.get("faq", []):
            documentos.append({
                "company_id": company_id,
                "titulo": f"{company_id} - FAQ - {item.get('question', '')}",
                "conteudo": (
                    f"Pergunta frequente: {item.get('question', '')}. "
                    f"Resposta: {item.get('answer', '')}"
                ),
                "fonte": "company_contexts.json",
            })

        for policy in policies:
            documentos.append({
                "company_id": company_id,
                "titulo": f"{company_id} - política e observação",
                "conteudo": (
                    f"Política ou observação importante: {policy}. "
                    f"Este texto responde perguntas sobre regras, limitações, alterações, "
                    f"promoções, campanhas e confirmação de informações."
                ),
                "fonte": "company_contexts.json",
            })

    return documentos


def montar_documentos_zoo_faq(data):
    documentos = []

    if isinstance(data, dict):
        items = data.get("faq", [])
        company_id = data.get("company_id", "FLX-001")
    else:
        items = data
        company_id = "FLX-001"

    for item in items:
        pergunta = item.get("question") or item.get("pergunta")
        resposta = item.get("answer") or item.get("resposta")

        if pergunta and resposta:
            documentos.append({
                "company_id": company_id,
                "titulo": f"{company_id} - FAQ externo - {pergunta}",
                "conteudo": (
                    f"Pergunta frequente: {pergunta}. "
                    f"Resposta: {resposta}"
                ),
                "fonte": "zoo_faq.json",
            })

    return documentos


def carregar_documentos():
    documentos = []

    company_contexts_path = ROOT_DIR / "data" / "company_contexts.json"
    zoo_faq_path = ROOT_DIR / "data" / "zoo_faq.json"

    if company_contexts_path.exists():
        data = json.loads(company_contexts_path.read_text(encoding="utf-8"))
        documentos.extend(montar_documentos_company_contexts(data))

    if zoo_faq_path.exists():
        data = json.loads(zoo_faq_path.read_text(encoding="utf-8"))
        documentos.extend(montar_documentos_zoo_faq(data))

    return documentos


def main():
    documentos = carregar_documentos()

    if not documentos:
        print("Nenhum documento encontrado para vetorizar.")
        return

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

        for doc in documentos:
            embedding = gerar_embedding(doc["conteudo"])

            conn.execute(
                text("""
                    INSERT INTO base_conhecimento
                    (company_id, titulo, conteudo, fonte, embedding)
                    VALUES
                    (:company_id, :titulo, :conteudo, :fonte, :embedding)
                """),
                {
                    "company_id": doc["company_id"],
                    "titulo": doc["titulo"],
                    "conteudo": doc["conteudo"],
                    "fonte": doc["fonte"],
                    "embedding": str(embedding),
                },
            )

            total += 1

        print(f"Base vetorizada com sucesso. {total} documentos inseridos.")


if __name__ == "__main__":
    main()
