from __future__ import annotations

import re
from datetime import date

from src.retrieval.models import AssembledContext

_MANAGER_LINE = re.compile(
    r"^-\s*((?:Mr|Ms|Mrs|Dr)\.\s+.+?)(?:\s+—\s+Having experience.+)?$",
    re.MULTILINE,
)


def extract_fund_manager_names(text: str) -> list[str]:
    """Parse 'Fund managers:' bullet lines from AMC parser output."""
    names: list[str] = []
    for match in _MANAGER_LINE.finditer(text):
        name = match.group(1).strip()
        if name and name not in names:
            names.append(name)
    return names


def fund_manager_chunk_from_context(context: AssembledContext) -> str | None:
    """Use the dedicated Fund Manager section only (not full page overview chunks)."""
    for chunk in context.chunks:
        if (chunk.section or "").strip().lower() == "fund manager":
            return chunk.text
    for chunk in context.chunks:
        if "fund managers:" in chunk.text.lower():
            return chunk.text
    return None


def build_fund_manager_answer(
    *,
    scheme_display_name: str,
    context: AssembledContext,
    citation_url: str,
    last_updated: date,
) -> str | None:
    """
    Deterministic fund-manager answer when corpus chunk lists managers explicitly.
    Avoids LLM + validator failures on long name lists.
    """
    body = fund_manager_chunk_from_context(context)
    if not body:
        return None
    names = extract_fund_manager_names(body)
    if not names:
        return None
    joined = ", ".join(names)
    # Citation URL and footer are added by validate_answer — do not embed URL in prose.
    return f"The fund managers of {scheme_display_name} are {joined}."
