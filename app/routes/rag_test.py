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
        request=request,
        name="rag_test.html",
        context={
            "company_id": company_id,
        },
    )


@router.post("/api/rag-test/perguntar")
def perguntar(req: PerguntaRequest):
    db = SessionLocal()

    try:
        # embedding da pergunta
        pergunta_embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=req.pergunta,
        ).data[0].embedding

        # busca vetorial
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

        if not rows:
            return {
                "resposta": "Não encontrei essa informação na base de conhecimento.",
                "fontes": [],
                "contextos_recuperados": [],
                "status": "sem_contexto",
            }

        # monta contexto
        contexto = "\n\n".join(
            [
                f"Título: {r.titulo}\nConteúdo: {r.conteudo}\nFonte: {r.fonte}"
                for r in rows
            ]
        )

        fontes = list(set([r.fonte for r in rows if r.fonte]))

        # chamada da LLM
        resposta_llm = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de atendimento.\n"
                        "Responda usando apenas o contexto fornecido.\n"
                        "Se não souber, diga que não encontrou a informação."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Pergunta:\n{req.pergunta}\n\n"
                        f"Contexto:\n{contexto}"
                    ),
                },
            ],
            temperature=0.2,
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
