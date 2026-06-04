from __future__ import annotations

import re
import unicodedata

from src.schemes.registry import SchemeRegistry


def normalize_query(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def resolve_scheme_id(
    message: str,
    *,
    explicit_scheme_id: str | None,
    registry: SchemeRegistry,
) -> str | None:
    """
    Prefer scheme named in the user message over the UI scheme picker.

    A stale sidebar selection (e.g. Large Cap) must not override “holdings in bank index”.
    See docs/scheme-aliases.md for precedence rules and alias catalogue.
    """
    from_message = registry.resolve_scheme_id(message)
    if from_message:
        return from_message
    if explicit_scheme_id and registry.is_valid_scheme_id(explicit_scheme_id):
        return explicit_scheme_id
    return None
