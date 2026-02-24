from langdetect import detect

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
    except Exception:
        lang = "pt"
    return lang if lang in ["pt", "en", "es"] else "pt"