from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.config.settings import get_settings
from src.guardrails.validator import (
    _clean_spaces,
    _ensure_footer,
    _enforce_sentence_cap,
    _URL_RE,
)
from src.retrieval.citations import is_public_citation_url
from src.schemes.registry import SchemeRegistry

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class StructuredTable:
    title: str | None
    columns: list[str]
    rows: list[list[str]]


@dataclass
class StructuredValidationResult:
    summary: str
    table: StructuredTable
    citation_url: str
    last_updated: date


def parse_structured_json(raw: str) -> dict[str, Any]:
    """Extract JSON object from LLM output (plain or fenced)."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty structured response")

    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in structured response")
    payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("Structured response must be a JSON object")
    return payload


def validate_structured_response(
    payload: dict[str, Any],
    *,
    registry: SchemeRegistry,
    citation_url: str | None,
    last_updated: date | None,
) -> StructuredValidationResult:
    settings = get_settings()
    allowed = settings.allowed_domain_list()

    summary = str(payload.get("summary") or "").strip()
    table_obj = payload.get("table")
    if not isinstance(table_obj, dict):
        raise ValueError("Missing 'table' object in structured response")

    title = table_obj.get("title")
    title_str = str(title).strip() if title else None

    columns = table_obj.get("columns")
    rows = table_obj.get("rows")
    if not isinstance(columns, list) or len(columns) < 2:
        raise ValueError("Table must have at least 2 columns")
    if not isinstance(rows, list) or len(rows) < 1:
        raise ValueError("Table must have at least 1 row")

    columns = [str(c).strip() for c in columns]
    normalized_rows: list[list[str]] = []
    for row in rows[: settings.structured_max_rows]:
        if not isinstance(row, list):
            continue
        cells = [str(cell).strip() for cell in row]
        while len(cells) < len(columns):
            cells.append("")
        normalized_rows.append(cells[: len(columns)])

    normalized_rows = _filter_rows_to_registry(normalized_rows, registry)
    if not normalized_rows:
        raise ValueError("No in-scope scheme rows in structured table")

    summary = _URL_RE.sub("", summary)
    summary = _clean_spaces(summary)
    summary = _enforce_sentence_cap(summary, max_sentences=settings.structured_summary_max_sentences)

    chosen = (
        citation_url
        if citation_url and is_public_citation_url(citation_url, allowed_domains=allowed)
        else ""
    )
    if not chosen:
        raise ValueError("Structured response requires an allowlisted citation URL")

    footer_date = last_updated or date.today()
    summary_with_footer = _ensure_footer(summary, footer_date) if summary else ""

    return StructuredValidationResult(
        summary=summary_with_footer,
        table=StructuredTable(title=title_str, columns=columns, rows=normalized_rows),
        citation_url=chosen,
        last_updated=footer_date,
    )


def structured_to_chat_dict(result: StructuredValidationResult) -> dict[str, Any]:
    """API payload for type=structured."""
    table = result.table
    summary = result.summary
    # Plain-text fallback for accessibility and clients that ignore structured.
    lines = []
    if summary:
        lines.append(summary)
    if table.title:
        lines.append(table.title)
    header_line = " | ".join(table.columns)
    lines.append(header_line)
    for row in table.rows:
        lines.append(" | ".join(row))
    answer = "\n".join(lines)

    return {
        "answer": answer,
        "citation_url": result.citation_url,
        "last_updated": result.last_updated.isoformat(),
        "type": "structured",
        "refusal_reason": None,
        "structured": {
            "format": "table",
            "title": table.title,
            "columns": table.columns,
            "rows": table.rows,
            "summary": summary or None,
        },
    }


def _filter_rows_to_registry(
    rows: list[list[str]],
    registry: SchemeRegistry,
) -> list[list[str]]:
    """Keep rows whose first column matches an in-scope scheme name or alias."""
    if not rows:
        return rows

    scheme_labels: list[str] = []
    for scheme in registry.list_schemes():
        scheme_labels.append(scheme.display_name.lower())
        scheme_labels.extend(a.lower() for a in scheme.aliases)
        for phrase in registry.search_phrases_for_scheme(scheme.scheme_id):
            if len(phrase) > 4:
                scheme_labels.append(phrase.lower())

    kept: list[list[str]] = []
    for row in rows:
        if not row:
            continue
        label = row[0].lower()
        if any(s in label or label in s for s in scheme_labels if s):
            kept.append(row)
    # If LLM used scheme_id in column 0, allow exact id match
    if not kept:
        valid_ids = {s.scheme_id for s in registry.list_schemes()}
        for row in rows:
            if row and row[0] in valid_ids:
                scheme = registry.get(row[0])
                if scheme:
                    display_row = [scheme.display_name, *row[1:]]
                    kept.append(display_row)
    return kept
