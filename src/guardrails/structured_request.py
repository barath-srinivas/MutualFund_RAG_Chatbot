from __future__ import annotations

import re

# Multi-scheme list / "all funds" style questions.
_MULTI_SCHEME = re.compile(
    r"\b("
    r"all\s+(?:the\s+)?(?:funds?|schemes?)|each\s+(?:fund|scheme)|every\s+(?:fund|scheme)|"
    r"list\s+(?:the\s+)?(?:expense|exit|load|fee|ter|minimum|benchmark|riskometer)"
    r")\b",
    re.IGNORECASE,
)

# Explicit table / tabular formatting requested by the user.
_TABLE_FORMAT = re.compile(
    r"\b("
    r"tabular(?:\s+format)?|table\s+format|in\s+a\s+table|as\s+a\s+table|"
    r"markdown\s+table|format\s+as\s+a\s+table|show\s+(?:this\s+)?(?:in|as)\s+a\s+table"
    r")\b",
    re.IGNORECASE,
)


def is_catalog_query(message: str) -> bool:
    """User asks for data across all / multiple in-scope schemes."""
    return bool(_MULTI_SCHEME.search(message))


def is_table_format_request(message: str) -> bool:
    """User explicitly asks for tabular presentation."""
    return bool(_TABLE_FORMAT.search(message))


def wants_structured_response(message: str) -> bool:
    """End-user requested a structured (table) response — not default short prose."""
    return is_catalog_query(message) or is_table_format_request(message)
