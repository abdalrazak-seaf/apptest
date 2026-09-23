"""Arabic-aware normalization for numeric inputs and search text.

Keep in sync with packages/i18n/src/normalize.ts (both share the same test cases).
"""

import re
import unicodedata

# Arabic-Indic (٠-٩) and Extended/Persian (۰-۹) digits -> ASCII.
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})
# Arabic decimal/thousands separators.
_DIGIT_MAP.update({ord("٫"): ".", ord("٬"): ","})

_TATWEEL = "ـ"
# Harakat, tanween, shadda, sukun, superscript alef, Quranic marks.
_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
_ALEF_VARIANTS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
_WHITESPACE = re.compile(r"\s+")


def normalize_digits(value: str) -> str:
    """Convert Arabic-Indic digits and separators to ASCII."""
    return value.translate(_DIGIT_MAP)


def parse_int(value: str) -> int | None:
    """Parse a user-typed integer such as '٩٠٬٠٠٠' or '90,000'. Returns None if invalid."""
    cleaned = normalize_digits(value).replace(",", "").replace(" ", "").strip()
    if not cleaned.isascii() or not cleaned.lstrip("-").isdigit():
        return None
    return int(cleaned)


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text for search matching (not for display)."""
    text = unicodedata.normalize("NFKC", text)
    text = normalize_digits(text)
    text = text.replace(_TATWEEL, "")
    text = _DIACRITICS.sub("", text)
    text = text.translate(_ALEF_VARIANTS)
    text = text.replace("ة", "ه").replace("ى", "ي")
    return _WHITESPACE.sub(" ", text).strip().lower()
