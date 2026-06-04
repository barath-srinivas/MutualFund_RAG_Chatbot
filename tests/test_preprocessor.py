"""Tests for query normalization and scheme resolution precedence."""

from __future__ import annotations

import pytest

from src.retrieval.preprocessor import normalize_query, resolve_scheme_id
from src.schemes.registry import SchemeRegistry, get_scheme_registry
from src.config.settings import get_settings
from tests.scheme_test_data import ALL_SCHEMES_INFORMAL, STALE_PICKER_SCHEME_ID


@pytest.fixture
def registry() -> SchemeRegistry:
    get_scheme_registry.cache_clear()
    get_settings.cache_clear()
    return get_scheme_registry()


@pytest.mark.parametrize(
    ("message", "explicit", "expected"),
    [
        ("holdings in bank index", "icici-large-cap", "icici-nifty-bank"),
        ("fund managers of nifty 500", "icici-nifty-bank", "icici-nifty-500"),
        ("large cap exit load", "icici-nifty-50", "icici-large-cap"),
        ("TER for manufacturing", "icici-phd", "icici-manufacturing"),
        ("expense ratio?", "icici-multi-asset", "icici-multi-asset"),
        ("expense ratio?", None, None),
    ],
)
def test_resolve_precedence_message_vs_picker(
    registry: SchemeRegistry,
    message: str,
    explicit: str | None,
    expected: str | None,
) -> None:
    assert (
        resolve_scheme_id(message, explicit_scheme_id=explicit, registry=registry)
        == expected
    )


def test_invalid_explicit_scheme_id_ignored_when_message_unresolved(
    registry: SchemeRegistry,
) -> None:
    assert (
        resolve_scheme_id(
            "What is the expense ratio?",
            explicit_scheme_id="not-a-real-scheme",
            registry=registry,
        )
        is None
    )


def test_normalize_query_collapses_whitespace_and_unicode() -> None:
    assert normalize_query("  bank\u00a0index  ") == "bank index"


@pytest.mark.parametrize(
    ("explicit", "expected"),
    [
        ("icici-nifty-bank", "icici-nifty-bank"),
        ("icici-large-cap", "icici-large-cap"),
    ],
)
def test_picker_used_when_message_has_no_scheme_hint(
    registry: SchemeRegistry, explicit: str, expected: str
) -> None:
    assert (
        resolve_scheme_id(
            "What is the exit load?",
            explicit_scheme_id=explicit,
            registry=registry,
        )
        == expected
    )


def test_groww_slug_in_message_overrides_picker(registry: SchemeRegistry) -> None:
    sid = resolve_scheme_id(
        "icici-prudential-nifty-bank-index-fund-direct-growth minimum SIP",
        explicit_scheme_id="icici-large-cap",
        registry=registry,
    )
    assert sid == "icici-nifty-bank"


@pytest.mark.parametrize(
    ("target_scheme_id", "phrase"),
    [(sid, phrase) for sid, phrase, _ in ALL_SCHEMES_INFORMAL],
)
def test_each_scheme_informal_phrase_overrides_stale_picker(
    registry: SchemeRegistry,
    target_scheme_id: str,
    phrase: str,
) -> None:
    stale = (
        "icici-nifty-bank"
        if target_scheme_id == STALE_PICKER_SCHEME_ID
        else STALE_PICKER_SCHEME_ID
    )
    message = f"What is the expense ratio for {phrase}?"
    assert (
        resolve_scheme_id(message, explicit_scheme_id=stale, registry=registry)
        == target_scheme_id
    )
