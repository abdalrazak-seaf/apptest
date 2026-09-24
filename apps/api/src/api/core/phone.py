"""Saudi mobile number normalization.

The MVP launches in Saudi Arabia, so only Saudi mobile numbers (05x / +9665x) are accepted.
Accepting a wider range later means replacing this module, not its callers.
"""

import re

from api.core.normalize import normalize_digits

# Saudi mobile subscriber numbers are 9 digits starting with 5.
_SUBSCRIBER = re.compile(r"^5\d{8}$")
_SEPARATORS = re.compile(r"[\s\-().]")


def normalize_saudi_phone(raw: str) -> str | None:
    """Return the number in E.164 (+9665XXXXXXXX), or None if it is not a Saudi mobile.

    Accepts Arabic-Indic digits and the formats people actually type:
    0501234567, 501234567, +966501234567, 00966501234567, 966501234567.
    """
    digits = _SEPARATORS.sub("", normalize_digits(raw.strip()))
    if digits.startswith("+"):
        digits = digits[1:]
    if not digits.isascii() or not digits.isdigit():
        return None

    if digits.startswith("00966"):
        subscriber = digits[5:]
    elif digits.startswith("966"):
        subscriber = digits[3:]
    elif digits.startswith("0"):
        subscriber = digits[1:]
    else:
        subscriber = digits

    return f"+966{subscriber}" if _SUBSCRIBER.match(subscriber) else None


def mask_phone(phone: str) -> str:
    """Mask a phone number for display and logs: +966501234567 -> +9665****4567."""
    if len(phone) < 8:
        return "*" * len(phone)
    return f"{phone[:5]}****{phone[-4:]}"
