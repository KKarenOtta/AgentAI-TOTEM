from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


DATA_PATH = Path("data/company_contexts.json")


def load_all_company_contexts() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return {}

    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_company_context(company_id: str) -> dict[str, Any]:
    data = load_all_company_contexts()
    context = data.get(company_id, {})

    if not isinstance(context, dict):
        return {}

    return context


def save_all_company_contexts(data: dict[str, Any]) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str) -> set[str]:
    ignored = {
        "a", "o", "os", "as", "um", "uma", "uns", "umas", "de", "da", "do",
        "das", "dos", "no", "na", "nos", "nas", "em", "para", "por", "com",
        "onde", "fica", "ficam", "tem", "tenho", "quero", "saber", "aqui"
    }

    return {
        token
        for token in normalize_text(value).split()
        if len(token) >= 3 and token not in ignored
    }


def _score(query: str, *values: str) -> int:
    query_tokens = _tokens(query)
    haystack = " ".join(normalize_text(value) for value in values)
    haystack_tokens = _tokens(haystack)

    score = len(query_tokens & haystack_tokens) * 3

    normalized_query = normalize_text(query)
    if normalized_query and normalized_query in haystack:
        score += 8

    return score


def answer_from_company_context(company_id: str, question: str) -> tuple[str, float, str]:
    context = load_company_context(company_id)

    if not context:
        return "", 0.0, "company_context_empty"

    question_norm = normalize_text(question)

    direct = _direct_answer(context, question_norm)
    if direct:
        return direct, 1.0, "company_context_rule"

    candidates: list[tuple[int, str]] = []

    for item in context.get("faq", []):
        score = _score(question, item.get("question", ""), item.get("answer", ""))
        if score:
            candidates.append((score + 5, item.get("answer", "")))

    for group_name in ["services", "stores", "attractions"]:
        for item in context.get(group_name, []):
            score = _score(
                question,
                item.get("name", ""),
                item.get("category", ""),
                item.get("zone", ""),
                item.get("reference", ""),
                " ".join(item.get("tags", [])),
            )

            if score:
                answer = _format_item_answer(item)
                candidates.append((score, answer))

    if not candidates:
        return "", 0.0, "company_context_no_match"

    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_answer = candidates[0]

    if best_score < 3:
        return "", 0.0, "company_context_low_score"

    confidence = min(0.95, best_score / 15)
    return best_answer, confidence, "company_context"


def _direct_answer(context: dict[str, Any], question_norm: str) -> str:
    location = context.get("location", {})
    contacts = context.get("contacts", {})
    hours = context.get("hours", {})

    if any(term in question_norm for term in ["endereco", "localizacao", "onde fica o zoologico", "onde fica o zoo"]):
        return (
            f"O endereço é {location.get('address')}. "
            f"Referência: {location.get('reference')}. "
            f"Mapa: {location.get('map_url') or location.get('official_map_url')}."
        )

    if any(term in question_norm for term in ["horario", "funcionamento", "abre", "fecha"]):
        return (
            f"O funcionamento informado nesta base é: segunda a sábado, {hours.get('monday_to_saturday')}; "
            f"domingo, {hours.get('sunday')}. Em feriados: {hours.get('holidays')}"
        )

    if any(term in question_norm for term in ["site", "telefone", "contato", "email"]):
        return (
            f"Site oficial: {contacts.get('site')}. "
            f"Telefone: {contacts.get('phone')}. "
            f"E-mail: {contacts.get('email')}."
        )

    if any(term in question_norm for term in ["mapa", "como chegar", "percurso"]):
        map_url = location.get("official_map_url") or location.get("map_url")
        return f"Use o mapa oficial para se localizar no percurso: {map_url}"

    return ""


def _format_item_answer(item: dict[str, Any]) -> str:
    name = item.get("name") or "Local"
    zone = item.get("zone")
    reference = item.get("reference")

    parts = [f"{name}:"]

    if zone:
        parts.append(f"fica na região {zone}.")

    if reference:
        parts.append(reference)

    return " ".join(parts).strip()
