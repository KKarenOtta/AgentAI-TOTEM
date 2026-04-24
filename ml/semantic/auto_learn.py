import json
from pathlib import Path

FAQ_FILE = Path("data/zoo_faq.json")

def learn(question, intent, answer):

    if not FAQ_FILE.exists():
        FAQ_FILE.write_text("[]", encoding="utf-8")

    data = json.loads(FAQ_FILE.read_text(encoding="utf-8"))

    # evita duplicação
    for item in data:
        if item["question"] == question:
            return

    data.append({
        "question": question,
        "answer": answer,
        "intent": intent
    })

    FAQ_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
