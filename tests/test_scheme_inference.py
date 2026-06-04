from __future__ import annotations

from src.ingest.scheme_inference import infer_scheme_id_from_text
from src.schemes.registry import get_scheme_registry


def test_infer_phd_from_pharma_name() -> None:
    text = (
        "ICICI Prudential Pharma Healthcare and Diagnostics (P.H.D) Fund Direct Growth. "
        "Expense ratio for direct plan is 0.89%."
    )
    assert infer_scheme_id_from_text(text, get_scheme_registry()) == "icici-phd"


def test_infer_does_not_map_nasdaq_to_phd() -> None:
    text = "ICICI Prudential NASDAQ 100 Index Fund Coca-Cola European Partners"
    assert infer_scheme_id_from_text(text, get_scheme_registry()) is None
