from __future__ import annotations

import hashlib
import re
from datetime import datetime

from src.ingest.models import DocumentChunk, DocumentSection, ParsedDocument
from src.ingest.scheme_inference import infer_scheme_id_from_text
from src.ingest.topic_tagger import tag_chunk_topic

# ~800 tokens at ~4 chars/token; 50–100 token overlap per architecture.md
MAX_CHUNK_CHARS = 3200
OVERLAP_CHARS = 400
MIN_CHUNK_CHARS = 40

_PDF_HEADING = re.compile(
    r"^(?:[A-Z][A-Z0-9\s/&\-]{2,60}|[0-9]+\.\s+[A-Z].{2,60})$",
)


def chunk_document(doc: ParsedDocument) -> list[DocumentChunk]:
    """Split a parsed document into section-based chunks with metadata (task 1.9)."""
    if doc.sections:
        return _chunk_from_sections(doc)
    if doc.pages:
        return _chunk_from_pdf_pages(doc)
    if doc.text.strip():
        return _split_text_into_chunks(
            doc,
            section="Document",
            text=doc.text.strip(),
            topic=tag_chunk_topic(section="Document", text=doc.text.strip(), manifest_topic=doc.manifest_topic),
        )
    return []


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _chunk_from_sections(doc: ParsedDocument) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for section in doc.sections:
        section_name = section.heading or "Untitled section"
        body = section.text.strip()
        if not body:
            continue
        topic = tag_chunk_topic(section=section_name, text=body, manifest_topic=doc.manifest_topic)
        chunks.extend(_split_text_into_chunks(doc, section=section_name, text=body, topic=topic))
    return chunks


def _chunk_from_pdf_pages(doc: ParsedDocument) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for index, page_text in enumerate(doc.pages, start=1):
        page_text = page_text.strip()
        if not page_text:
            continue
        section_name, body = _detect_pdf_section(page_text, index)
        topic = tag_chunk_topic(section=section_name, text=body, manifest_topic=doc.manifest_topic)
        chunks.extend(_split_text_into_chunks(doc, section=section_name, text=body, topic=topic))
    return chunks


def _detect_pdf_section(page_text: str, page_number: int) -> tuple[str, str]:
    lines = page_text.splitlines()
    for line in lines[:8]:
        candidate = line.strip()
        if _PDF_HEADING.match(candidate) and len(candidate) <= 80:
            return candidate, page_text
    return f"Page {page_number}", page_text


def _split_text_into_chunks(
    doc: ParsedDocument,
    *,
    section: str,
    text: str,
    topic: str | None,
) -> list[DocumentChunk]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [_build_chunk(doc, section=section, text=text, topic=topic, part=0)]

    chunks: list[DocumentChunk] = []
    start = 0
    part = 0
    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        if end < len(text):
            break_at = text.rfind("\n\n", start, end)
            if break_at <= start:
                break_at = text.rfind(" ", start, end)
            if break_at > start:
                end = break_at
        piece = text[start:end].strip()
        if len(piece) >= MIN_CHUNK_CHARS or end >= len(text):
            section_label = section if part == 0 else f"{section} (part {part + 1})"
            chunks.append(_build_chunk(doc, section=section_label, text=piece, topic=topic, part=part))
            part += 1
        if end >= len(text):
            break
        start = max(end - OVERLAP_CHARS, start + 1)
    return chunks


def _build_chunk(
    doc: ParsedDocument,
    *,
    section: str,
    text: str,
    topic: str | None,
    part: int,
) -> DocumentChunk:
    th = text_hash(text)
    chunk_id = f"{doc.source_id}:{part:04d}:{th[:16]}"
    scheme_id = doc.scheme_id
    if scheme_id is None:
        inferred = infer_scheme_id_from_text(f"{section}\n{text}")
        if inferred:
            scheme_id = inferred
    return DocumentChunk(
        chunk_id=chunk_id,
        scheme_id=scheme_id,
        doc_type=doc.doc_type,
        source_url=doc.source_url,
        source_id=doc.source_id,
        section=section,
        topic=topic,
        fetched_at=doc.fetched_at,
        text_hash=th,
        content_hash=doc.content_hash,
        text=text,
    )


def sections_from_parsed(parsed_sections: list[dict]) -> list[DocumentSection]:
    """Convert parser section dicts into DocumentSection objects."""
    return [
        DocumentSection(
            heading=str(item.get("heading") or ""),
            level=int(item.get("level") or 0),
            text=str(item.get("text") or ""),
            tables=list(item.get("tables") or []),
        )
        for item in parsed_sections
    ]
