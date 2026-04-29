import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from openai import OpenAI

from app.database.session import SessionLocal
from fastapi.templating import Jinja2Templates

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
            "company_id": company_id
        }
    )


@router.post("/api/rag-test/perguntar")
def perguntar(req: PerguntaRequest):
    db = SessionLocal()

    try:
        pergunta_embedding = client.embeddings.create(
            model="text-embedding-3-small",
            input=req.pergunta
        ).data[0].embedding

        rows = db.execute(
            text("""
                SELECT titulo, conteudo, fonte
                FROM base_conhecimento
                WHERE company_id = :company_id
                ORDER BY embedding <-> CAST(:embedding AS vector)
                LIMIT 3
            """),
            {
                "company_id": req.company_id,
                "embedding": str(pergunta_embedding)
            }
        ).fetchall()

        if not rows:
            return {
                "resposta": "Não encontrei informações suficientes na base de conhecimento.",
                "fontes": [],
                "status": "sem_contexto"
            }

        contexto = "\n\n".join(
            [f"Título: {r.titulo}\nConteúdo: {r.conteudo}\nFonte: {r.fonte}" for r in rows]
        )

        fontes = list(set([r.fonte for r in rows if r.fonte]))

        resposta_llm = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de atendimento da Flex Media. "
                        "Responda em português do Brasil. "
                        "Use somente o contexto fornecido. "
                        "Se não souber, diga que não encontrou a informação na base."
                    )
                },
                {
                    "role": "user",
                    "content": f"Pergunta do usuário: {req.pergunta}\n\nContexto recuperado:\n{contexto}"
                }
            ],
            temperature=0.2
        )

        return {
            "resposta": resposta_llm.choices[0].message.content,
            "fontes": fontes,
            "contextos_recuperados": [
                {
                    "titulo": r.titulo,
                    "conteudo": r.conteudo,
                    "fonte": r.fonte
                }
                for r in rows
            ],
            "status": "ok"
        }

    finally:
        db.close()
