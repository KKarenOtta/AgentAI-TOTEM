from ml.semantic.retriever import search_knowledge

docs = search_knowledge(
    company_id="FLX-001",
    query="quais instalações existem no zoológico",
    top_k=5,
)

print("\nRESULTADOS:\n")

for doc in docs:
    print("=" * 50)
    print("SCORE:", doc["score"])
    print("TITULO:", doc["titulo"])
    print("CONTEUDO:", doc["conteudo"])
    print()
