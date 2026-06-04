from __future__ import annotations

import re

# Phase 2.10: PII input guard (block common identifiers).
# Keep this intentionally simple and conservative; do not log the raw input.
_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR = re.compile(r"\b[2-9]\d{11}\b")
_PHONE = re.compile(r"\b\d{10}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Bank account numbers vary; we avoid an overly broad rule to reduce false positives.
_ACCOUNT_LIKE = re.compile(r"\b\d{9,18}\b")


def detect_pii(text: str) -> bool:
    if not text:
        return False
    if _PAN.search(text):
        return True
    if _AADHAAR.search(text):
        return True
    if _EMAIL.search(text):
        return True
    if _PHONE.search(text):
        return True
    # Only treat generic long numbers as PII if the user is explicitly sharing account info-like words.
    if re.search(r"\b(account|a\/c|bank|ifsc|upi|otp)\b", text, re.IGNORECASE) and _ACCOUNT_LIKE.search(text):
        return True
    return False

