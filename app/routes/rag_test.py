import os

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


class PerguntaRequest(BaseModel):
    company_id: str = "FLX-001"
    pergunta: str


@router.get("/rag-test/{company_id}", response_class=HTMLResponse)
def tela_rag_test(request: Request, company_id: str):
    return templates.TemplateResponse(
        "rag_test.html",
        {
            "request": request,
            "company_id": company_id,
        },
    )


@router.post("/api/rag-test/perguntar")
def perguntar(req: PerguntaRequest):
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
                LIMIT 3
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

        resposta_llm = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de atendimento da Flex Media.\n"
                        "REGRA OBRIGATÓRIA: responda usando exclusivamente o CONTEXTO fornecido.\n"
                        "Não use conhecimento externo.\n"
                        "Não invente telefones, sites, preços, horários, endereços ou informações que não estejam no contexto.\n"
                        "Se a resposta não estiver claramente no contexto, responda exatamente:\n"
                        "'Não encontrei essa informação na base de conhecimento.'\n"
                        "Responda em português do Brasil, de forma curta e objetiva."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"PERGUNTA:\n{req.pergunta}\n\n"
                        f"CONTEXTO AUTORIZADO:\n{contexto}"
                    ),
                },
            ],
            temperature=0,
        )

        return {
            "resposta": resposta_llm.choices[0].message.content,
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
            "status": "ok",
        }

    finally:
        db.close()
