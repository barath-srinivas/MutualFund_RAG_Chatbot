from __future__ import annotations

import json
from pathlib import Path

from src.ingest.amc_spa import extract_fund_id_from_url, resolve_direct_growth_scheme_code
from src.ingest.fetcher import content_hash_bytes
from src.ingest.manifest import SourceEntry
from src.ingest.parsers import parse_document
from src.ingest.parsers.amc_fund_parser import parse_amc_product_bundle
from src.ingest.fetcher import FetchResult
from datetime import datetime, timezone

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CANONICAL_URL = (
    "https://www.icicipruamc.com/mutual-fund/index-funds/"
    "icici-prudential-nifty-50-index-fund/57"
)


def test_extract_fund_id_from_url() -> None:
    assert extract_fund_id_from_url(CANONICAL_URL) == "57"
    assert extract_fund_id_from_url(CANONICAL_URL + "/") == "57"


def test_parse_amc_product_bundle_includes_fund_and_page_text() -> None:
    fund_api = json.loads((FIXTURES / "nifty50_fund_api.json").read_text(encoding="utf-8"))
    bundle = json.dumps(
        {
            "page_url": CANONICAL_URL,
            "fund_id": "57",
            "page_text": "ICICI Prudential\nNifty 50 Index Fund\nInvestment Objective\nTrack Nifty 50",
            "fund_api": fund_api,
        }
    ).encode("utf-8")

    parsed = parse_amc_product_bundle(bundle)
    text = parsed["text"]
    assert "Nifty 50" in text
    assert CANONICAL_URL in text
    assert "latestNav" in text or "Latest NAV" in text or "31.6435" in text
    assert parsed["sections"]


def test_parse_document_routes_amc_product_page() -> None:
    fund_api = json.loads((FIXTURES / "nifty50_fund_api.json").read_text(encoding="utf-8"))
    content = json.dumps(
        {
            "page_url": CANONICAL_URL,
            "fund_id": "57",
            "page_text": "Nifty 50 Index Fund\nDirect - Growth",
            "fund_api": fund_api,
        }
    ).encode("utf-8")
    entry = SourceEntry(
        id="icici-nifty-50-amc-product-page",
        url=CANONICAL_URL,
        doc_type="amc_product_page",
        scheme_id="icici-nifty-50",
    )
    fetch = FetchResult(
        source_id=entry.id,
        url=entry.url,
        status_code=200,
        content=content,
        content_type="application/json",
        fetched_at=datetime.now(timezone.utc),
        content_hash=content_hash_bytes(content),
    )
    doc = parse_document(entry, fetch)
    assert "Nifty 50" in doc.text
    assert doc.scheme_id == "icici-nifty-50"


def test_resolve_direct_growth_scheme_code() -> None:
    fund_api = json.loads((FIXTURES / "nifty_bank_fund_api.json").read_text(encoding="utf-8"))
    assert resolve_direct_growth_scheme_code(fund_api) == "9675"


def test_parse_bundle_includes_top_holdings() -> None:
    fund_api = json.loads((FIXTURES / "nifty_bank_fund_api.json").read_text(encoding="utf-8"))
    holdings = json.loads((FIXTURES / "nifty_bank_holdings.json").read_text(encoding="utf-8"))
    bundle = json.dumps(
        {
            "page_url": "https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-bank-index-fund/1839",
            "fund_id": "1839",
            "scheme_code": "9675",
            "page_text": "",
            "fund_api": fund_api,
            "tab_sections": {
                "Fund Manager": "Mr. Ajaykumar Solanki\nHaving experience of 11 years\nMr. Nishit Patel\nHaving experience of 8 years"
            },
            "extra_apis": {"portfolio_holdings": holdings},
        }
    ).encode("utf-8")
    parsed = parse_amc_product_bundle(bundle)
    text = parsed["text"]
    assert "HDFC Bank Ltd." in text
    assert "18.92" in text
    assert "Fund managers" in text or "Mr. Ajaykumar Solanki" in text
    assert any(s.get("heading") == "Top holdings" for s in parsed["sections"])
