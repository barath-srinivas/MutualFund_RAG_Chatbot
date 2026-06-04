from __future__ import annotations

from datetime import date

import pytest

from src.guardrails.validator import validate_answer


def test_validator_strips_urls_from_body_and_sets_citation_field() -> None:
    draft = "Expense ratio is 0.85%. https://example.com https://www.icicipruamc.com/foo"
    result = validate_answer(
        draft,
        citation_url="https://www.icicipruamc.com/foo",
        last_updated=date(2026, 5, 31),
    )
    assert result.citation_url == "https://www.icicipruamc.com/foo"
    assert "http" not in result.answer
    assert "Last updated from sources: 2026-05-31" in result.answer


def test_validator_truncates_to_three_sentences() -> None:
    draft = (
        "One. Two. Three. Four. https://www.icicipruamc.com/foo "
        "Last updated from sources: 2026-05-31"
    )
    result = validate_answer(
        draft,
        citation_url="https://www.icicipruamc.com/foo",
        last_updated=date(2026, 5, 31),
    )
    # Should include only first 3 sentences at most.
    assert result.answer.startswith("One. Two. Three.")


def test_validator_strips_meta_commentary_about_context() -> None:
    draft = (
        "The NAV of ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund "
        "Direct Growth is 44.93 as on 05/29/2026. "
        "This information is available in the context provided. "
        "The context does not provide any additional information about the NAV other than the date and value."
    )
    result = validate_answer(
        draft,
        citation_url="https://www.icicipruamc.com/mutual-fund/equity-funds/foo/1657",
        last_updated=date(2026, 6, 1),
    )
    assert "44.93" in result.answer
    assert "context" not in result.answer.lower()
    assert "additional information" not in result.answer.lower()


@pytest.mark.parametrize(
    "meta_sentence",
    [
        "This information is available in the context provided.",
        "The context does not provide any additional information.",
        "No additional information is available in the sources.",
    ],
)
def test_validator_strips_various_meta_commentary(meta_sentence: str) -> None:
    draft = f"The NAV is 44.93 as on 05/29/2026. {meta_sentence}"
    result = validate_answer(
        draft,
        citation_url="https://www.icicipruamc.com/mutual-fund/index-funds/foo/1839",
        last_updated=date(2026, 6, 1),
    )
    assert "44.93" in result.answer
    assert "context" not in result.answer.lower()
    assert "additional information" not in result.answer.lower()


def test_validator_keeps_answer_when_only_meta_removed() -> None:
    draft = (
        "The expense ratio is 0.53% p.a. "
        "This information is available in the context provided."
    )
    result = validate_answer(
        draft,
        citation_url="https://www.icicipruamc.com/mutual-fund/hybrid-funds/foo/55",
        last_updated=date(2026, 6, 1),
    )
    assert "0.53%" in result.answer


def test_validator_does_not_split_on_honorific_abbreviations() -> None:
    draft = (
        "The fund managers are Mr. Nishit Patel, Ms. Ashwini Shinde, Mr. Nikhil Kabra, "
        "Mr. Venus Ahuja, and Mr. Darshil Dedhia."
    )
    result = validate_answer(
        draft,
        citation_url="https://www.icicipruamc.com/mutual-fund/index-funds/foo/1884",
        last_updated=date(2026, 6, 1),
        max_sentences=3,
    )
    assert "Nikhil Kabra" in result.answer
    assert "Darshil Dedhia" in result.answer

