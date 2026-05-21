from ml.semantic.retriever import ask_rag

result = ask_rag(
    company_id="FLX-001",
    question="quais são as instalações do zoológico?"
)

print("\n=== RESPOSTA FINAL ===\n")
print(result["answer"])
