from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from src.ingest.chunker import chunk_document, sections_from_parsed, text_hash
from src.ingest.topic_tagger import is_fund_management_heading, tag_chunk_topic
from src.ingest.fetcher import DocumentFetcher, FetchResult, content_hash_bytes, is_url_allowed
from src.ingest.manifest import CorpusManifest, SourceEntry, load_manifest
from src.ingest.models import ParsedDocument
from src.ingest.parsers import parse_document
from src.ingest.parsers.html_parser import parse_html
from src.ingest.parsers.pdf_parser import parse_pdf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_manifest_loads_and_schema() -> None:
    manifest = load_manifest(PROJECT_ROOT / "corpus" / "urls.yaml")
    assert manifest.version == 2
    assert manifest.amc == "ICICI Prudential Mutual Fund"
    assert len(manifest.factsheet_canonical) == 10
    sources = manifest.all_sources()
    assert len(sources) == 10
    for entry in sources:
        assert entry.id
        assert entry.url.startswith("https://")
        assert entry.allowed_for_citation is True
        assert entry.doc_type in {
            "factsheet",
            "kim",
            "sid",
            "amc_scheme",
            "amc_product_page",
            "amc_faq",
            "amfi",
            "sebi",
        }


def test_factsheet_canonical_per_scheme() -> None:
    manifest = load_manifest(PROJECT_ROOT / "corpus" / "urls.yaml")
    for scheme_id in manifest.factsheet_canonical:
        url = manifest.factsheet_url_for_scheme(scheme_id)
        assert url is not None
        assert is_url_allowed(url, ["icicipruamc.com", "www.icicipruamc.com"])
        assert "www.icicipruamc.com/mutual-fund/" in url

    nifty_url = manifest.factsheet_url_for_scheme("icici-nifty-50")
    assert nifty_url is not None
    assert "icici-prudential-nifty-50-index-fund/57" in nifty_url
    assert nifty_url.startswith("https://www.icicipruamc.com/")


def test_coverage_matrix_exists() -> None:
    matrix = PROJECT_ROOT / "corpus" / "coverage-matrix.md"
    assert matrix.is_file()
    text = matrix.read_text(encoding="utf-8")
    assert "icici-manufacturing" in text
    assert "fund_management" in text.lower() or "IDX" in text


def test_is_url_allowed_subdomains() -> None:
    allowed = ["icicipruamc.com", "amfiindia.com", "sebi.gov.in"]
    assert is_url_allowed("https://digitalfactsheet.icicipruamc.com/fact/foo.php", allowed)
    assert is_url_allowed("https://www.amfiindia.com/investor", allowed)
    assert not is_url_allowed("https://groww.in/mutual-funds/foo", allowed)


def test_fetcher_success_and_raw_save(tmp_path: Path) -> None:
    html = b"<html><body><p>Expense ratio 1.2%</p></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html, headers={"Content-Type": "text/html"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    entry = SourceEntry(
        id="test-html",
        url="https://www.icicipruamc.com/test",
        doc_type="amc_scheme",
        scheme_id="icici-large-cap",
    )

    with DocumentFetcher(
        raw_dir=tmp_path,
        allowed_domains=["icicipruamc.com"],
        client=client,
        rate_limit_seconds=0,
        retries=1,
    ) as fetcher:
        result = fetcher.fetch_source(entry, save_raw=True)

    assert result.ok
    assert result.status_code == 200
    assert result.content_hash == content_hash_bytes(html)
    assert result.raw_path is not None
    assert result.raw_path.exists()


def test_fetcher_rejects_disallowed_domain() -> None:
    entry = SourceEntry(
        id="bad",
        url="https://groww.in/mutual-funds/foo",
        doc_type="factsheet",
        scheme_id="icici-large-cap",
    )
    with DocumentFetcher(allowed_domains=["icicipruamc.com"], rate_limit_seconds=0) as fetcher:
        result = fetcher.fetch_source(entry, save_raw=False)
    assert not result.ok
    assert result.error is not None
    assert "allowlist" in result.error.lower()


def test_fetcher_retries_on_failure() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            return httpx.Response(503)
        return httpx.Response(200, content=b"ok", headers={"Content-Type": "text/plain"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    entry = SourceEntry(
        id="retry-test",
        url="https://www.icicipruamc.com/retry",
        doc_type="amc_faq",
    )

    with DocumentFetcher(
        allowed_domains=["icicipruamc.com"],
        client=client,
        rate_limit_seconds=0,
        retries=3,
    ) as fetcher:
        result = fetcher.fetch_source(entry, save_raw=False)

    assert result.ok
    assert calls["count"] == 2


def test_html_parser_strips_nav_and_extracts_manager() -> None:
    html = (FIXTURES / "sample_factsheet.html").read_bytes()
    parsed = parse_html(html)
    assert "nav" not in parsed["text"].lower() or "Home | Contact" not in parsed["text"]
    assert "Fund Manager" in parsed["text"] or "Jane Doe" in parsed["text"]
    assert "0.85%" in parsed["text"]
    assert any("Direct Growth" in table for table in parsed["tables"])


def test_pdf_parser_minimal_pdf() -> None:
    # Minimal valid PDF structure may not extract well; test empty handling
    parsed = parse_pdf(b"not a pdf")
    assert parsed["warnings"]
    assert parsed["text"] == ""


def test_parse_document_routes_html() -> None:
    entry = SourceEntry(
        id="html-doc",
        url="https://digitalfactsheet.icicipruamc.com/fact/test.php",
        doc_type="amc_scheme",
        scheme_id="icici-manufacturing",
    )
    fetch = FetchResult(
        source_id=entry.id,
        url=entry.url,
        status_code=200,
        content=(FIXTURES / "sample_factsheet.html").read_bytes(),
        content_type="text/html",
        fetched_at=datetime.now(timezone.utc),
        content_hash="abc",
    )
    doc = parse_document(entry, fetch)
    assert doc.scheme_id == "icici-manufacturing"
    assert "Jane Doe" in doc.text or "Fund Manager" in doc.text


def test_parse_document_failed_fetch() -> None:
    entry = SourceEntry(id="x", url="https://www.icicipruamc.com/x", doc_type="kim")
    fetch = FetchResult(
        source_id="x",
        url=entry.url,
        status_code=404,
        content=b"",
        content_type="text/html",
        fetched_at=datetime.now(timezone.utc),
        content_hash="",
        error="HTTP 404",
    )
    doc = parse_document(entry, fetch)
    assert doc.text == ""
    assert doc.parse_warnings


def test_html_parser_returns_sections() -> None:
    html = (FIXTURES / "sample_factsheet.html").read_bytes()
    parsed = parse_html(html)
    assert parsed["sections"]
    headings = [s["heading"] for s in parsed["sections"]]
    assert "Fund Manager" in headings
    assert "Expense ratio" in headings


def test_html_parser_strips_header_footer_and_nav() -> None:
    html = b"""<!DOCTYPE html>
<html><body>
<header role="banner">Site header</header>
<nav class="navbar">Home | Contact</nav>
<main>
  <h1>Sample Fund</h1>
  <p>Minimum SIP Rs. 100.</p>
</main>
<footer id="site-footer">Copyright AMC</footer>
<aside role="complementary">Related links</aside>
</body></html>"""
    parsed = parse_html(html)
    lower = parsed["text"].lower()
    assert "home | contact" not in lower
    assert "copyright amc" not in lower
    assert "site header" not in lower
    assert "related links" not in lower
    assert "minimum sip" in lower


def test_chunk_metadata_required_fields() -> None:
    fetched = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
    entry = SourceEntry(
        id="html-doc",
        url="https://digitalfactsheet.icicipruamc.com/fact/test.php",
        doc_type="amc_scheme",
        scheme_id="icici-manufacturing",
    )
    fetch = FetchResult(
        source_id=entry.id,
        url=entry.url,
        status_code=200,
        content=(FIXTURES / "sample_factsheet.html").read_bytes(),
        content_type="text/html",
        fetched_at=fetched,
        content_hash="abc123",
    )
    doc = parse_document(entry, fetch)
    chunks = chunk_document(doc)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.chunk_id
        assert chunk.scheme_id == "icici-manufacturing"
        assert chunk.doc_type == "amc_scheme"
        assert chunk.source_url == entry.url
        assert chunk.section
        assert chunk.fetched_at == fetched
        assert chunk.text_hash == text_hash(chunk.text)
        assert chunk.content_hash == "abc123"
        assert chunk.text.strip()


def test_fund_manager_section_gets_topic_tag() -> None:
    fetched = datetime(2026, 5, 31, tzinfo=timezone.utc)
    doc = parse_document(
        SourceEntry(
            id="mgr",
            url="https://www.icicipruamc.com/scheme",
            doc_type="amc_scheme",
            scheme_id="icici-large-cap",
        ),
        FetchResult(
            source_id="mgr",
            url="https://www.icicipruamc.com/scheme",
            status_code=200,
            content=(FIXTURES / "sample_factsheet.html").read_bytes(),
            content_type="text/html",
            fetched_at=fetched,
            content_hash="hash",
        ),
    )
    chunks = chunk_document(doc)
    manager_chunks = [c for c in chunks if c.topic == "fund_management"]
    assert manager_chunks
    assert any("Jane Doe" in c.text for c in manager_chunks)


def test_pdf_page_chunking() -> None:
    doc = ParsedDocument(
        source_id="pdf-1",
        source_url="https://www.icicipruamc.com/doc.pdf",
        doc_type="factsheet",
        scheme_id="icici-large-cap",
        content_type="application/pdf",
        text="page one\n\npage two",
        pages=["Expense ratio 1.05% for direct plan.", "Exit load 1% within 365 days."],
        fetched_at=datetime(2026, 5, 31, tzinfo=timezone.utc),
        content_hash="pdfhash",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 2
    assert all(c.section.startswith("Page") for c in chunks)
    assert any(c.topic == "fees" for c in chunks)


def test_large_section_splits_with_overlap() -> None:
    body = ("Expense ratio details. " * 400).strip()
    doc = ParsedDocument(
        source_id="big",
        source_url="https://www.icicipruamc.com/big",
        doc_type="kim",
        scheme_id="icici-large-cap",
        content_type="text/html",
        text=body,
        sections=sections_from_parsed([{"heading": "Fees", "level": 2, "text": body, "tables": []}]),
        fetched_at=datetime(2026, 5, 31, tzinfo=timezone.utc),
        content_hash="big",
    )
    chunks = chunk_document(doc)
    assert len(chunks) > 1
    assert chunks[0].section == "Fees"
    assert "(part" in chunks[1].section


@pytest.mark.parametrize(
    "heading",
    [
        "Fund Manager",
        "Fund Managers",
        "Investment Team",
        "Fund Management",
        "Portfolio Manager",
        "Investment Manager",
        "Fund Manager (part 2)",
    ],
)
def test_fund_management_heading_patterns(heading: str) -> None:
    assert is_fund_management_heading(heading)
    assert tag_chunk_topic(section=heading, text="Jane Doe manages the scheme.") == "fund_management"


@pytest.mark.parametrize(
    "heading",
    ["Expense ratio", "Exit load", "Overview", "Performance", "Document"],
)
def test_non_fund_management_headings(heading: str) -> None:
    assert not is_fund_management_heading(heading)


def test_managed_by_in_body_without_heading_does_not_tag_fund_management() -> None:
    topic = tag_chunk_topic(
        section="Overview",
        text="The scheme is managed by Jane Doe since 2020.",
    )
    assert topic != "fund_management"


def test_manifest_topic_overrides_inference() -> None:
    assert tag_chunk_topic(
        section="Overview",
        text="Generic text.",
        manifest_topic="fund_management",
    ) == "fund_management"


def test_index_mandate_section_tagged_as_fund_management() -> None:
    topic = tag_chunk_topic(
        section="Investment Objective",
        text="The scheme is an index fund replicating the Nifty 50 Index passively.",
    )
    assert topic == "fund_management"


def test_fees_and_benchmark_topics_from_heading() -> None:
    assert tag_chunk_topic(section="Expense ratio", text="Direct plan TER 0.85%.") == "fees"
    assert tag_chunk_topic(section="Risk profile", text="Riskometer: Very High.") == "benchmark"
