from __future__ import annotations

import re
from datetime import date

from src.retrieval.models import AssembledContext

_HOLDING_LINE = re.compile(r"^\d+\.\s+(.+?):\s+([\d.]+)%\s*$", re.MULTILINE)
_HOLDING_TABLE_LINE = re.compile(r"^(.+?)\s*\|\s*([\d.]+)\s*$", re.MULTILINE)


def extract_holdings_rows(text: str) -> list[tuple[str, str]]:
    """Parse numbered holdings lines from AMC parser output."""
    rows: list[tuple[str, str]] = []
    for match in _HOLDING_LINE.finditer(text):
        name = match.group(1).strip()
        weight = match.group(2).strip()
        if name and weight:
            rows.append((name, weight))
    if rows:
        return rows
    for match in _HOLDING_TABLE_LINE.finditer(text):
        name = match.group(1).strip()
        if name.lower() == "company":
            continue
        weight = match.group(2).strip()
        if name and weight:
            rows.append((name, weight))
    return rows


def holdings_chunk_from_context(context: AssembledContext) -> str | None:
    """Use the dedicated Top holdings section only."""
    for chunk in context.chunks:
        if (chunk.section or "").strip().lower() == "top holdings":
            return chunk.text
    for chunk in context.chunks:
        if "top holdings by portfolio weight" in chunk.text.lower():
            return chunk.text
    return None


def format_holdings_phrase(rows: list[tuple[str, str]], *, max_names: int = 10) -> str:
    shown = rows[:max_names]
    parts = [f"{name} ({weight}%)" for name, weight in shown]
    return ", ".join(parts)


def build_holdings_answer(
    *,
    scheme_display_name: str,
    context: AssembledContext,
    citation_url: str,
    last_updated: date,
) -> str | None:
    """
    Deterministic holdings answer when corpus chunk lists companies and weights.
    Avoids LLM missing the Top holdings section when sector allocation is also retrieved.
    """
    body = holdings_chunk_from_context(context)
    if not body:
        return None
    rows = extract_holdings_rows(body)
    if not rows:
        return None
    phrase = format_holdings_phrase(rows)
    return (
        f"The top holdings of {scheme_display_name} by portfolio weight are {phrase}."
    )
