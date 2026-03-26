class ResponseAgent:
    def generate_fallback(self, intent: str) -> str:
        if intent == "promotion":
            return "Posso mostrar as promoções mais relevantes para você agora."

        if intent == "product":
            return "Posso recomendar produtos e ofertas com base no que você procura."

        if intent == "support":
            return "Posso ajudar com atendimento, dúvidas e resolução de problemas."

        return "Posso ajudar com informações, ofertas, produtos e suporte."
