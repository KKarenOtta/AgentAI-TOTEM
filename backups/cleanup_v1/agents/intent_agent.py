from dataclasses import dataclass


@dataclass(slots=True)
class IntentResult:
    label: str
    confidence: float


class IntentAgent:
    def detect(self, message: str) -> IntentResult:
        text = (message or "").strip().lower()

        if not text:
            return IntentResult(label="general", confidence=0.30)

        promotion_terms = ("promo", "desconto", "oferta", "cupom")
        product_terms = ("produto", "item", "comprar", "recomende")
        support_terms = ("ajuda", "suporte", "problema", "atendimento", "resolver")

        if any(term in text for term in promotion_terms):
            return IntentResult(label="promotion", confidence=0.93)

        if any(term in text for term in product_terms):
            return IntentResult(label="product", confidence=0.90)

        if any(term in text for term in support_terms):
            return IntentResult(label="support", confidence=0.91)

        return IntentResult(label="general", confidence=0.65)
