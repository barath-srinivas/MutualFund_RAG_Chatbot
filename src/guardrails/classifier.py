from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.guardrails.structured_request import is_catalog_query, wants_structured_response
from src.schemes.registry import SchemeRegistry

RouteLabel = Literal[
    "factual",
    "performance",
    "advisory",
    "out_of_scope",
    "operational_shared",
    "structured",
]

_ADVISORY = re.compile(
    r"\b("
    r"should\s+i|recommend|advice|suggest|which\s+fund|better|best|good\s+manager|"
    r"best\s+manager|is\s+.*manager\s+good|worth\s+investing|should\s+we|should\s+my"
    r")\b",
    re.IGNORECASE,
)
_MANAGER_COMPARISON = re.compile(
    r"\b(manager).*(better|best|good|vs|versus|compare|comparison)\b|\b(better|best).*(manager)\b",
    re.IGNORECASE,
)
_PERFORMANCE = re.compile(
    r"\b("
    r"return|returns|cagr|xirr|performance|alpha|sharpe|drawdown|"
    r"1y|3y|5y|one\s+year|three\s+year|five\s+year"
    r")\b",
    re.IGNORECASE,
)
_OPERATIONAL = re.compile(
    r"\b(download|capital\s+gain|account\s+statement|statement|folio|cas|how\s+to\s+download)\b",
    re.IGNORECASE,
)
_AMC_HINT = re.compile(
    r"\b(hdfc|sbi|nippon|aditya\s*birla|axis|kotak|mirae|uti|franklin|dsp|icici\s*prudential)\b",
    re.IGNORECASE,
)


@dataclass
class ClassificationResult:
    label: RouteLabel
    scheme_id: str | None
    reason: str


def classify_query(
    *,
    message: str,
    registry: SchemeRegistry,
    explicit_scheme_id: str | None,
    resolved_scheme_id: str | None,
) -> ClassificationResult:
    text = message.strip()

    if explicit_scheme_id and not registry.is_valid_scheme_id(explicit_scheme_id):
        return ClassificationResult("out_of_scope", None, "invalid_explicit_scheme")

    if _ADVISORY.search(text) or _MANAGER_COMPARISON.search(text):
        return ClassificationResult("advisory", resolved_scheme_id, "advisory_keywords")

    if _PERFORMANCE.search(text):
        return ClassificationResult("performance", resolved_scheme_id, "performance_keywords")

    if _OPERATIONAL.search(text):
        return ClassificationResult("operational_shared", resolved_scheme_id, "operational_keywords")

    if wants_structured_response(text):
        return ClassificationResult(
            "structured",
            resolved_scheme_id,
            "multi_scheme_catalog" if is_catalog_query(text) else "table_format_requested",
        )

    if resolved_scheme_id is None and _AMC_HINT.search(text):
        # Mentioned a likely AMC/fund family but not in our scoped scheme list.
        return ClassificationResult("out_of_scope", None, "unknown_scheme_or_amc")

    return ClassificationResult("factual", resolved_scheme_id, "default_factual")

