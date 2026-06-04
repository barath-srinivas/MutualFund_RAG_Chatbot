from __future__ import annotations

import json
from datetime import date

import pytest

from src.guardrails.structured_request import (
    is_catalog_query,
    is_table_format_request,
    wants_structured_response,
)
from src.guardrails.structured_response import (
    parse_structured_json,
    structured_to_chat_dict,
    validate_structured_response,
)
from src.schemes.registry import get_scheme_registry


def test_wants_structured_for_table_or_all_funds() -> None:
    assert wants_structured_response("List expense ratio of all funds in tabular format")
    assert is_table_format_request("Show in a table please")
    assert is_catalog_query("expense ratio for each scheme")
    assert not wants_structured_response("What is the expense ratio of Large Cap?")


def test_parse_structured_json_from_fence() -> None:
    raw = """Here is the data:
```json
{"summary": "Test.", "table": {"columns": ["A", "B"], "rows": [["X", "1"]]}}
```"""
    data = parse_structured_json(raw)
    assert data["table"]["columns"] == ["A", "B"]


def test_validate_structured_filters_in_scope_rows() -> None:
    registry = get_scheme_registry()
    payload = {
        "summary": "Expense ratios for supported schemes.",
        "table": {
            "title": "TER",
            "columns": ["Scheme", "TER"],
            "rows": [
                ["Random ETF", "0.1%"],
                ["ICICI Prudential Multi Asset Fund", "0.53% p.a."],
            ],
        },
    }
    result = validate_structured_response(
        payload,
        registry=registry,
        citation_url="https://www.icicipruamc.com/foo",
        last_updated=date(2026, 6, 1),
    )
    assert len(result.table.rows) == 1
    assert "Multi Asset" in result.table.rows[0][0]


def test_structured_to_chat_dict_type() -> None:
    registry = get_scheme_registry()
    payload = {
        "summary": "Summary line.",
        "table": {
            "columns": ["Scheme", "Value"],
            "rows": [["ICICI Prudential Nifty 50 Index Direct Plan Growth", "0.2%"]],
        },
    }
    result = validate_structured_response(
        payload,
        registry=registry,
        citation_url="https://www.icicipruamc.com/foo",
        last_updated=date(2026, 6, 1),
    )
    out = structured_to_chat_dict(result)
    assert out["type"] == "structured"
    assert out["structured"]["format"] == "table"
    assert len(out["structured"]["rows"]) >= 1
