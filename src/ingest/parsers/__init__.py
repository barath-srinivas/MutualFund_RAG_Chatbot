from src.ingest.chunker import sections_from_parsed
from src.ingest.fetcher import FetchResult
from src.ingest.manifest import SourceEntry
from src.ingest.models import ParsedDocument
from src.ingest.parsers.amc_fund_parser import parse_amc_product_bundle
from src.ingest.parsers.html_parser import parse_html
from src.ingest.parsers.pdf_parser import parse_pdf


def parse_document(entry: SourceEntry, fetch: FetchResult) -> ParsedDocument:
    """Route fetch result to PDF or HTML parser (tasks 1.7, 1.8)."""
    if not fetch.ok:
        return ParsedDocument(
            source_id=entry.id,
            source_url=entry.url,
            doc_type=entry.doc_type,
            scheme_id=entry.scheme_id,
            content_type=fetch.content_type,
            text="",
            fetched_at=fetch.fetched_at,
            content_hash=fetch.content_hash,
            parse_warnings=[fetch.error or f"HTTP {fetch.status_code}"],
        )

    content_type = (fetch.content_type or "").lower()
    is_pdf = "pdf" in content_type or fetch.content[:4] == b"%PDF"

    if entry.doc_type == "amc_product_page":
        parsed = parse_amc_product_bundle(fetch.content)
    elif is_pdf:
        parsed = parse_pdf(fetch.content)
    else:
        parsed = parse_html(fetch.content)

    return ParsedDocument(
        source_id=entry.id,
        source_url=entry.url,
        doc_type=entry.doc_type,
        scheme_id=entry.scheme_id,
        content_type=fetch.content_type,
        text=parsed["text"],
        pages=parsed.get("pages", []),
        tables=parsed.get("tables", []),
        sections=sections_from_parsed(parsed.get("sections", [])),
        manifest_topic=entry.topic,
        fetched_at=fetch.fetched_at,
        content_hash=fetch.content_hash,
        parse_warnings=parsed.get("warnings", []),
    )
