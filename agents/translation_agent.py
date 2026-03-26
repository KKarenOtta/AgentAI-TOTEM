from __future__ import annotations

from services.translation.translator import TranslatorService


class TranslationAgent:
    def __init__(self) -> None:
        self.translator = TranslatorService()

    def translate(self, text: str, target_language: str) -> str:
        return self.translator.translate(text=text, target_language=target_language)
