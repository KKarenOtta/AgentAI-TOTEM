from __future__ import annotations


class TranslatorService:
    def translate(self, text: str, target_language: str) -> str:
        text = (text or "").strip()
        target_language = (target_language or "").strip().lower()

        if not text:
            return ""

        if target_language in {"pt", "pt-br", "portuguese"}:
            return text

        if target_language in {"en", "english"}:
            return f"[EN] {text}"

        if target_language in {"es", "spanish"}:
            return f"[ES] {text}"

        return text
