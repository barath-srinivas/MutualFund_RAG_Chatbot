"""Corpus ingest: fetch, parse, chunk, embed, and index official documents."""

from src.ingest.chunker import chunk_document
from src.ingest.embedder import LocalBgeEmbedder, create_embedder
from src.ingest.fetcher import DocumentFetcher, FetchResult
from src.ingest.manifest import CorpusManifest, SourceEntry, load_manifest
from src.ingest.models import DocumentChunk, ParsedDocument
from src.ingest.parsers import parse_document
from src.ingest.pipeline import IngestRunReport, format_dry_run_summary, run_ingest
from src.ingest.topic_tagger import tag_chunk_topic
from src.ingest.vector_store import ChromaVectorStore

__all__ = [
    "ChromaVectorStore",
    "CorpusManifest",
    "DocumentChunk",
    "DocumentFetcher",
    "FetchResult",
    "IngestRunReport",
    "LocalBgeEmbedder",
    "ParsedDocument",
    "SourceEntry",
    "chunk_document",
    "create_embedder",
    "format_dry_run_summary",
    "load_manifest",
    "parse_document",
    "run_ingest",
    "tag_chunk_topic",
]
