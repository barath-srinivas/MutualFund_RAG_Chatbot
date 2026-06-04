from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    score: float
    scheme_id: str | None
    doc_type: str
    source_url: str
    section: str
    topic: str | None
    fetched_at: datetime | None = None


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk] = field(default_factory=list)
    best_score: float = 0.0
    low_confidence: bool = True


@dataclass
class AssembledContext:
    context_text: str
    chunks: list[RetrievedChunk]
    citation_urls: list[str]
    last_updated: date | None
