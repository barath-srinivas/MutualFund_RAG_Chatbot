from __future__ import annotations

import pytest

from src.config.settings import get_settings
from src.ingest.manifest import load_manifest
from src.retrieval.citations import (
    is_public_citation_url,
    preferred_citation_url,
)
from tests.scheme_test_data import ALL_SCHEMES_INFORMAL


def test_rejects_chrome_extension_and_factsheet_pdf() -> None:
    allowed = get_settings().allowed_domain_list()
    assert not is_public_citation_url(
        "chrome-extension://efaidnbmnnnibpcajpcglclefindmkaj/"
        "https://digitalfactsheet.icicipruamc.com/fact/pdf/fund-factsheet-for-january-2026.pdf",
        allowed_domains=allowed,
    )
    assert not is_public_citation_url(
        "https://digitalfactsheet.icicipruamc.com/fact/pdf/fund-factsheet-for-january-2026.pdf",
        allowed_domains=allowed,
    )
    assert is_public_citation_url(
        "https://www.icicipruamc.com/mutual-fund/equity-funds/icici-prudential-large-cap-fund/211",
        allowed_domains=allowed,
    )


def test_preferred_citation_uses_canonical_amc_page() -> None:
    manifest = load_manifest()
    allowed = get_settings().allowed_domain_list()
    url = preferred_citation_url(
        scheme_id="icici-large-cap",
        candidate_urls=[
            "https://digitalfactsheet.icicipruamc.com/fact/pdf/fund-factsheet-for-january-2026.pdf"
        ],
        manifest=manifest,
        allowed_domains=allowed,
    )
    assert url == manifest.factsheet_url_for_scheme("icici-large-cap")
    assert "www.icicipruamc.com" in (url or "")


@pytest.mark.parametrize(
    ("scheme_id", "url_fragment"),
    [(sid, frag) for sid, _phrase, frag in ALL_SCHEMES_INFORMAL],
)
def test_canonical_urls_for_all_ten_schemes(scheme_id: str, url_fragment: str) -> None:
    manifest = load_manifest()
    allowed = get_settings().allowed_domain_list()
    url = preferred_citation_url(
        scheme_id=scheme_id,
        candidate_urls=[],
        manifest=manifest,
        allowed_domains=allowed,
    )
    assert url is not None
    assert url_fragment in url


def test_bank_and_large_cap_canonical_urls_are_distinct() -> None:
    manifest = load_manifest()
    bank = manifest.factsheet_url_for_scheme("icici-nifty-bank")
    large = manifest.factsheet_url_for_scheme("icici-large-cap")
    assert bank and large and bank != large
