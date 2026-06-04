from __future__ import annotations

import re

from src.schemes.registry import SchemeRegistry, get_scheme_registry


def infer_scheme_id_from_text(
    text: str,
    registry: SchemeRegistry | None = None,
) -> str | None:
    """
    Match chunk text to an in-scope scheme using display names and aliases.
    Used for multi-scheme PDFs (combined factsheets) where scheme_id is null at source level.
    """
    reg = registry or get_scheme_registry()
    lowered = text.lower()
    best_id: str | None = None
    best_len = 0

    for scheme in reg.list_schemes():
        candidates = reg.search_phrases_for_scheme(scheme.scheme_id)
        for phrase in candidates:
            key = phrase.lower().strip()
            if len(key) < 8:
                continue
            if key in lowered and len(key) > best_len:
                best_id = scheme.scheme_id
                best_len = len(key)

    return best_id


def infer_scheme_id_from_section_heading(
    heading: str,
    registry: SchemeRegistry | None = None,
) -> str | None:
    """Prefer section titles like 'ICICI Prudential Large Cap Fund' on factsheet pages."""
    return infer_scheme_id_from_text(heading, registry)
