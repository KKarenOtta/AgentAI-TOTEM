from __future__ import annotations

import json
from pathlib import Path


FAQ_DIR = Path("data/faq")
OUT_PATH = Path("data/ml/intent/dataset.jsonl")
SEED_PATH = Path("data/ml/intent/seed_dataset.jsonl")


SEED_ROWS = [
    {"text": "qual o horário de funcionamento", "intent": "business_hours"},
    {"text": "que horas abre", "intent": "business_hours"},
    {"text": "que horas fecha", "intent": "business_hours"},
    {"text": "vocês funcionam hoje", "intent": "business_hours"},
    {"text": "o parque está aberto agora", "intent": "business_hours"},
    {"text": "qual o horário de abertura", "intent": "business_hours"},
    {"text": "qual o horário de encerramento", "intent": "business_hours"},
    {"text": "até que horas posso entrar", "intent": "business_hours"},

    {"text": "onde ficam os pinguins", "intent": "location_animal"},
    {"text": "onde estão os pinguins", "intent": "location_animal"},
    {"text": "quero ver os leões", "intent": "location_animal"},
    {"text": "onde ficam os elefantes", "intent": "location_animal"},
    {"text": "onde encontro as girafas", "intent": "location_animal"},
    {"text": "como chego nos macacos", "intent": "location_animal"},
    {"text": "onde ficam os répteis", "intent": "location_animal"},
    {"text": "onde posso ver os animais", "intent": "location_animal"},

    {"text": "onde ficam as flores", "intent": "location_place"},
    {"text": "onde fica o jardim", "intent": "location_place"},
    {"text": "onde é a entrada principal", "intent": "location_place"},
    {"text": "como chego na saída", "intent": "location_place"},
    {"text": "onde fica o mapa", "intent": "location_place"},
    {"text": "onde fica a área infantil", "intent": "location_place"},
    {"text": "onde fica o aquário", "intent": "location_place"},
    {"text": "como chegar na bilheteria", "intent": "location_place"},

    {"text": "onde posso comer", "intent": "food"},
    {"text": "quero comida", "intent": "food"},
    {"text": "tem restaurante aqui", "intent": "food"},
    {"text": "onde fica a lanchonete", "intent": "food"},
    {"text": "tem praça de alimentação", "intent": "food"},
    {"text": "onde compro água", "intent": "food"},
    {"text": "onde posso tomar café", "intent": "food"},
    {"text": "tem lugar para lanchar", "intent": "food"},

    {"text": "tem banheiro", "intent": "infrastructure"},
    {"text": "onde fica o banheiro", "intent": "infrastructure"},
    {"text": "tem fraldário", "intent": "infrastructure"},
    {"text": "onde fica o bebedouro", "intent": "infrastructure"},
    {"text": "tem acessibilidade", "intent": "infrastructure"},
    {"text": "onde fica o estacionamento", "intent": "infrastructure"},
    {"text": "tem guarda volumes", "intent": "infrastructure"},
    {"text": "onde pego informação", "intent": "infrastructure"},

    {"text": "tem desconto hoje", "intent": "promotion"},
    {"text": "quero uma promoção", "intent": "promotion"},
    {"text": "tem cupom disponível", "intent": "promotion"},
    {"text": "existe desconto para família", "intent": "promotion"},
    {"text": "quais ofertas estão disponíveis", "intent": "promotion"},
    {"text": "tem promoção de ingresso", "intent": "promotion"},
    {"text": "como consigo desconto", "intent": "promotion"},
    {"text": "tem campanha ativa", "intent": "promotion"},
]


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _load_seed_rows() -> list[dict[str, str]]:
    if not SEED_PATH.exists():
        SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SEED_PATH.open("w", encoding="utf-8") as file:
            for row in SEED_ROWS:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    rows = []

    for line in SEED_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        item = json.loads(line)
        text = str(item.get("text") or "").strip()
        intent = str(item.get("intent") or "").strip()

        if text and intent:
            rows.append({"text": text, "intent": intent})

    return rows


def _load_faq_rows() -> list[dict[str, str]]:
    rows = []

    for faq_file in FAQ_DIR.glob("*/faq.json"):
        try:
            items = json.loads(faq_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for item in items:
            question = str(item.get("question") or "").strip()
            intent = str(item.get("intent") or "").strip()

            if question and intent and intent != "geral":
                rows.append({"text": question, "intent": intent})

    return rows


def build() -> dict[str, int]:
    merged = {}
    rows = _load_seed_rows() + _load_faq_rows()

    for row in rows:
        key = (_normalize(row["text"]), row["intent"])
        merged[key] = {
            "text": row["text"].strip(),
            "intent": row["intent"].strip(),
        }

    final_rows = list(merged.values())

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", encoding="utf-8") as file:
        for row in final_rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "rows": len(final_rows),
        "seed_rows": len(_load_seed_rows()),
        "faq_rows": len(_load_faq_rows()),
    }

    print(f"[intent_dataset] {report}")
    return report


if __name__ == "__main__":
    build()
