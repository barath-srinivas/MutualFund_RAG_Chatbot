from __future__ import annotations

import pytest

from src.guardrails.classifier import classify_query
from src.schemes.registry import get_scheme_registry


@pytest.mark.parametrize(
    ("message", "expected_label"),
    [
        ("Should I invest in Technology fund?", "advisory"),
        ("Which fund is better, Large Cap or Flexicap?", "advisory"),
        ("Is the Pharma fund manager good?", "advisory"),
        ("What was 5Y return of Large Cap?", "performance"),
        ("Show 3 year CAGR for Nifty 50", "performance"),
        ("How to download capital gains statement?", "operational_shared"),
        ("Download account statement for my folio", "operational_shared"),
        ("HDFC Top 100 expense ratio?", "out_of_scope"),
        ("SBI Small Cap exit load", "out_of_scope"),
        ("Expense ratio of ICICI Large Cap?", "factual"),
        ("Who manages Flexicap fund?", "factual"),
        ("Benchmark for Nifty Next 50?", "factual"),
        ("List the expense ratio of all the funds in a tabular format", "structured"),
        ("Expense ratio for each scheme", "structured"),
        ("Show expense ratio in a table format", "structured"),
    ],
)
def test_classifier_routes(message: str, expected_label: str) -> None:
    registry = get_scheme_registry()
    resolved = registry.resolve_scheme_id(message)
    result = classify_query(
        message=message,
        registry=registry,
        explicit_scheme_id=None,
        resolved_scheme_id=resolved,
    )
    assert result.label == expected_label

