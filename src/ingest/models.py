from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DocumentSection:
    """Structured section extracted from HTML (heading boundary)."""

    heading: str
    level: int
    text: str
    tables: list[str] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Normalized text extracted from a fetched source."""

    source_id: str
    source_url: str
    doc_type: str
    scheme_id: str | None
    content_type: str
    text: str
    pages: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    sections: list[DocumentSection] = field(default_factory=list)
    manifest_topic: str | None = None
    fetched_at: datetime | None = None
    content_hash: str = ""
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class DocumentChunk:
    """Single retrievable chunk with required metadata (task 1.9)."""

    chunk_id: str
    scheme_id: str | None
    doc_type: str
    source_url: str
    source_id: str
    section: str
    topic: str | None
    fetched_at: datetime | None
    text_hash: str
    content_hash: str
    text: str
