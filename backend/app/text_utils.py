import re

# кириллица => латиница для определения языка
_CYRILLIC = re.compile(r"[а-яёіїєґ]")
_LATIN_KZ_HINTS = re.compile(r"[әғқңөұүһіӘҒҚҢӨҰҮҺІ]")


def detect_language(text: str) -> str:
    """Простое определение языка: казахский или русский."""
    text = (text or "").strip()
    if not text:
        return "ru"
    if _LATIN_KZ_HINTS.search(text):
        return "kz"
    cyrillic_count = len(_CYRILLIC.findall(text))
    if cyrillic_count == 0:
        return "ru"
    # специфичные казахские буквы => kz
    kz_specific = len(re.findall(r"[әғқңөұүһіә]", text, re.IGNORECASE))
    total = len(text)
    ratio = cyrillic_count / max(total, 1)
    if kz_specific >= 1 and ratio > 0.2:
        return "kz"
    return "ru"


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
