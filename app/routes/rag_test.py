import os
import re

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import text

from DB.session import SessionLocal


router = APIRouter(tags=["rag-test"])

templates = Jinja2Templates(directory="templates")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


COMPANY_DATA = {
    "FLX-001": {
        "name": "Zoológico de Demonstração",
        "business_type": "zoologico_com_centro_comercial",
        "description": "Base pública demonstrativa com informações sobre atrações, lojas, alimentação, serviços e atendimento.",
        "location": {
            "address": "Endereço fictício, 123 - Cidade/UF",
            "reference": "Próximo à entrada principal",
        },
        "hours": {
            "monday_to_saturday": "10:00 às 17:00",
            "sunday": "12:00 às 18:00",
            "holidays": "Consultar programação oficial antes da visita.",
        },
        "contacts": {
            "phone": "(11) 0000-0000",
            "email": "atendimento@example.com",
            "site": "https://example.com",
        },
        "services": [
            {
                "name": "Banheiros principais",
                "category": "banheiro",
                "zone": "praça de alimentação",
                "reference": "Ficam no térreo, próximos à praça de alimentação.",
                "tags": ["banheiro", "toalete", "wc"],
            },
            {
                "name": "Praça de alimentação",
                "category": "alimentação",
                "zone": "área central",
                "reference": "Área central do percurso, próxima aos banheiros principais.",
                "tags": ["comida", "lanche", "refeição"],
            },
            {
                "name": "Loja de lembranças",
                "category": "loja",
                "zone": "saída",
                "reference": "Localizada próxima à saída do percurso.",
                "tags": ["loja", "souvenir", "presente"],
            },
        ],
        "faq": [
            {
                "question": "Onde posso comer?",
                "answer": "Você pode comer na praça de alimentação, que fica na área central do percurso, próxima aos banheiros principais.",
            },
            {
                "question": "Onde comprar salgado?",
                "answer": "Procure a praça de alimentação. Ela reúne opções de lanches, café, sorvete e refeições rápidas.",
            },
            {
                "question": "Onde ficam os pinguins?",
                "answer": "A área dos pinguins fica próxima à loja temática.",
            },
            {
                "question": "Qual o horário de funcionamento?",
                "answer": "O funcionamento informado nesta base é de segunda a sábado das 10:00 às 17:00 e domingo das 12:00 às 18:00.",
            },
        ],
        "policies": [
            "Horários e atrações podem sofrer alteração operacional.",
            "Informações não encontradas na base local devem ser confirmadas com a equipe ou no site oficial.",
        ],
    }
}


class PerguntaRequest(BaseModel):
    company_id: str = "FLX-001"
    pergunta: str


@router.get("/rag-test/{company_id}", response_class=HTMLResponse)
def tela_rag_test(request: Request, company_id: str):
    return templates.TemplateResponse(
        request=request,
        name="rag_test.html",
        context={
            "company_id": company_id,
        },
    )


def responder_com_llm_controlada(pergunta: str, contexto: str) -> str:
    resposta_llm = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um assistente de atendimento da Flex Media.\n"
                    "Responda de forma natural, clara e amigável.\n"
                    "Use exclusivamente os dados do CONTEXTO fornecido.\n"
                    "Não invente, não altere e não complete telefones, e-mails, sites, horários, preços, endereços ou nomes.\n"
                    "Se algum dado não estiver no contexto, não mencione esse dado.\n"
                    "Se a resposta não puder ser feita com o contexto, responda exatamente:\n"
                    "'Não encontrei essa informação na base de conhecimento.'\n"
                    "Responda em português do Brasil."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"PERGUNTA:\n{pergunta}\n\n"
                    f"CONTEXTO FECHADO:\n{contexto}"
                ),
            },
        ],
        temperature=0,
    )

    resposta = resposta_llm.choices[0].message.content

    numeros_resposta = set(re.findall(r"\d+", resposta))
    numeros_contexto = set(re.findall(r"\d+", contexto))

    if numeros_resposta - numeros_contexto:
        return "Não encontrei essa informação na base de conhecimento."

    return resposta


def contexto_estruturado(company_id: str, pergunta: str):
    data = COMPANY_DATA.get(company_id)

    if not data:
        return None

    p = pergunta.lower()

    if any(x in p for x in ["telefone", "celular", "whatsapp", "contato", "ligar"]):
        c = data["contacts"]
        return (
            "Informações de contato disponíveis:\n"
            f"Telefone: {c['phone']}\n"
            f"E-mail: {c['email']}\n"
            f"Site: {c['site']}"
        )

    if any(x in p for x in ["email", "e-mail"]):
        c = data["contacts"]
        return (
            "Informações de e-mail disponíveis:\n"
            f"E-mail: {c['email']}"
        )

    if any(x in p for x in ["site", "website", "link"]):
        c = data["contacts"]
        return (
            "Informações de site disponíveis:\n"
            f"Site: {c['site']}"
        )

    if any(x in p for x in ["endereço", "endereco", "localização", "localizacao", "onde fica"]):
        loc = data["location"]
        return (
            "Informações de localização disponíveis:\n"
            f"Endereço: {loc['address']}\n"
            f"Referência: {loc['reference']}"
        )

    if any(x in p for x in ["horário", "horario", "funcionamento", "abre", "fecha", "domingo"]):
        h = data["hours"]
        return (
            "Informações de funcionamento disponíveis:\n"
            f"Segunda a sábado: {h['monday_to_saturday']}\n"
            f"Domingo: {h['sunday']}\n"
            f"Feriados: {h['holidays']}"
        )

    if any(x in p for x in ["comer", "comida", "alimentação", "alimentacao", "lanche", "salgado", "refeição", "refeicao"]):
        return (
            "Informações sobre alimentação disponíveis:\n"
            "Você pode comer na praça de alimentação, que fica na área central do percurso, próxima aos banheiros principais."
        )

    if any(x in p for x in ["banheiro", "toalete", "wc"]):
        return (
            "Informações sobre banheiros disponíveis:\n"
            "Os banheiros principais ficam no térreo, próximos à praça de alimentação."
        )

    if any(x in p for x in ["loja", "lembrança", "lembranca", "souvenir", "presente"]):
        return (
            "Informações sobre loja disponíveis:\n"
            "A loja de lembranças fica próxima à saída do percurso."
        )

    if "pinguim" in p or "pinguins" in p:
        return (
            "Informações sobre pinguins disponíveis:\n"
            "A área dos pinguins fica próxima à loja temática."
        )

    if any(x in p for x in ["nome", "qual zoológico", "qual zoologico"]):
        return (
            "Informações institucionais disponíveis:\n"
            f"Nome: {data['name']}\n"
            f"Descrição: {data['description']}"
        )

    return None


@router.post("/api/rag-test/perguntar")
def perguntar(req: PerguntaRequest):
    contexto_fechado = contexto_estruturado(req.company_id, req.pergunta)

    if contexto_fechado:
        resposta = responder_com_llm_controlada(
            pergunta=req.pergunta,
            contexto=contexto_fechado,
        )

        return {
            "resposta": resposta,
            "fontes": ["company_data"],
            "contextos_recuperados": [
                {
                    "titulo": "Contexto estruturado",
                    "conteudo": contexto_fechado,
                    "fonte": "company_data",
                    "distancia": 0,
                }
            ],
            "status": "ok_contexto_fechado",
        }

    db = SessionLocal()

    try:
        pergunta_embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=req.pergunta,
        ).data[0].embedding

        rows = db.execute(
            text("""
                SELECT 
                    titulo,
                    conteudo,
                    fonte,
                    embedding <-> CAST(:embedding AS vector) AS distancia
                FROM base_conhecimento
                WHERE company_id = :company_id
                ORDER BY distancia
                LIMIT 5
            """),
            {
                "company_id": req.company_id,
                "embedding": str(pergunta_embedding),
            },
        ).fetchall()

        if not rows or rows[0].distancia > 0.8:
            return {
                "resposta": "Não encontrei essa informação na base de conhecimento.",
                "fontes": [],
                "contextos_recuperados": [],
                "status": "sem_contexto",
            }

        contexto = "\n\n".join(
            [
                f"Título: {r.titulo}\nConteúdo: {r.conteudo}\nFonte: {r.fonte}"
                for r in rows
            ]
        )

        fontes = list(set([r.fonte for r in rows if r.fonte]))

        resposta = responder_com_llm_controlada(
            pergunta=req.pergunta,
            contexto=contexto,
        )

        return {
            "resposta": resposta,
            "fontes": fontes,
            "contextos_recuperados": [
                {
                    "titulo": r.titulo,
                    "conteudo": r.conteudo,
                    "fonte": r.fonte,
                    "distancia": float(r.distancia),
                }
                for r in rows
            ],
            "status": "ok_rag",
        }

    finally:
        db.close()
