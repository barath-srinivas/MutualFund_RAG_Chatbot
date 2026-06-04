from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import PROJECT_ROOT, get_settings
from src.ingest.chunker import chunk_document
from src.ingest.embedder import Embedder, create_embedder
from src.ingest.fetcher import DocumentFetcher
from src.ingest.manifest import CorpusManifest, SourceEntry, load_manifest
from src.ingest.parsers import parse_document
from src.ingest.vector_store import ChromaVectorStore, VectorStore

logger = logging.getLogger(__name__)


@dataclass
class SourceRunResult:
    source_id: str
    url: str
    doc_type: str
    scheme_id: str | None
    status: str
    content_hash: str = ""
    chunks: int = 0
    skipped: bool = False
    error: str | None = None
    parse_warnings: list[str] = field(default_factory=list)


@dataclass
class IngestRunReport:
    run_id: str
    started_at: str
    finished_at: str
    dry_run: bool
    manifest_path: str
    embedding_model: str
    vector_db_path: str
    sources_processed: int
    sources_failed: int
    sources_skipped: int
    total_chunks: int
    chunks_by_scheme: dict[str, int]
    sources: list[SourceRunResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sources"] = [asdict(source) for source in self.sources]
        return data


def run_ingest(
    *,
    manifest_path: Path | None = None,
    dry_run: bool = False,
    save_raw: bool = True,
    source_ids: list[str] | None = None,
    force: bool = False,
    embedder: Embedder | None = None,
    vector_store: VectorStore | None = None,
) -> IngestRunReport:
    """Fetch, parse, chunk, embed, and persist corpus sources (tasks 1.11–1.14)."""
    settings = get_settings()
    manifest_file = manifest_path or settings.corpus_urls_path
    manifest = load_manifest(manifest_file)

    started = datetime.now(timezone.utc)
    run_id = started.strftime("ingest_%Y%m%dT%H%M%SZ")

    entries = _select_sources(manifest, source_ids)
    chunks_by_scheme: dict[str, int] = {}
    source_results: list[SourceRunResult] = []
    errors: list[str] = []

    active_embedder = None if dry_run else (embedder or create_embedder())
    store = None if dry_run else (vector_store or ChromaVectorStore())

    if not dry_run and store is not None and source_ids is None:
        _purge_orphaned_sources(manifest, store)

    with DocumentFetcher(raw_dir=settings.corpus_raw_path) as fetcher:
        for entry in entries:
            result = _process_source(
                entry,
                fetcher=fetcher,
                save_raw=save_raw,
                dry_run=dry_run,
                force=force,
                embedder=active_embedder,
                vector_store=store,
            )
            source_results.append(result)
            if result.error:
                errors.append(f"{entry.id}: {result.error}")
            if result.chunks and result.scheme_id:
                chunks_by_scheme[result.scheme_id] = chunks_by_scheme.get(result.scheme_id, 0) + result.chunks
            elif result.chunks and not result.scheme_id:
                chunks_by_scheme["_shared"] = chunks_by_scheme.get("_shared", 0) + result.chunks

    finished = datetime.now(timezone.utc)
    report = IngestRunReport(
        run_id=run_id,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        dry_run=dry_run,
        manifest_path=str(manifest_file),
        embedding_model=active_embedder.model_name if active_embedder else settings.embedding_model,
        vector_db_path=str(settings.vector_db_path),
        sources_processed=len(entries),
        sources_failed=sum(1 for item in source_results if item.status == "failed"),
        sources_skipped=sum(1 for item in source_results if item.skipped),
        total_chunks=sum(item.chunks for item in source_results),
        chunks_by_scheme=dict(sorted(chunks_by_scheme.items())),
        sources=source_results,
        errors=errors,
    )

    manifest_out = _write_run_manifest(report)
    logger.info(
        "Ingest %s complete: %s chunks, %s failed, %s skipped (manifest: %s)",
        "dry-run" if dry_run else "run",
        report.total_chunks,
        report.sources_failed,
        report.sources_skipped,
        manifest_out,
    )
    return report


def _purge_orphaned_sources(manifest: CorpusManifest, store: VectorStore) -> None:
    """Remove indexed chunks whose source_id is no longer in the manifest."""
    allowed = {entry.id for entry in manifest.all_sources()}
    if not hasattr(store, "list_source_ids"):
        return
    for source_id in store.list_source_ids():  # type: ignore[attr-defined]
        if source_id not in allowed:
            removed = store.delete_source(source_id)
            logger.info("Purged %s orphaned chunks for source %s", removed, source_id)


def _select_sources(manifest: CorpusManifest, source_ids: list[str] | None) -> list[SourceEntry]:
    entries = manifest.all_sources()
    if not source_ids:
        return entries
    wanted = set(source_ids)
    selected = [entry for entry in entries if entry.id in wanted]
    missing = wanted - {entry.id for entry in selected}
    if missing:
        raise ValueError(f"Unknown source id(s): {', '.join(sorted(missing))}")
    return selected


def _process_source(
    entry: SourceEntry,
    *,
    fetcher: DocumentFetcher,
    save_raw: bool,
    dry_run: bool,
    force: bool,
    embedder: Embedder | None,
    vector_store: VectorStore | None,
) -> SourceRunResult:
    fetch = fetcher.fetch_source(entry, save_raw=save_raw)
    if not fetch.ok:
        return SourceRunResult(
            source_id=entry.id,
            url=entry.url,
            doc_type=entry.doc_type,
            scheme_id=entry.scheme_id,
            status="failed",
            error=fetch.error or f"HTTP {fetch.status_code}",
        )

    parsed = parse_document(entry, fetch)
    chunks = chunk_document(parsed)
    if not chunks:
        return SourceRunResult(
            source_id=entry.id,
            url=entry.url,
            doc_type=entry.doc_type,
            scheme_id=entry.scheme_id,
            status="failed",
            content_hash=fetch.content_hash,
            error="No chunks produced",
            parse_warnings=parsed.parse_warnings,
        )

    if dry_run:
        return SourceRunResult(
            source_id=entry.id,
            url=entry.url,
            doc_type=entry.doc_type,
            scheme_id=entry.scheme_id,
            status="dry_run",
            content_hash=fetch.content_hash,
            chunks=len(chunks),
            parse_warnings=parsed.parse_warnings,
        )

    assert embedder is not None
    assert vector_store is not None

    existing_hash = vector_store.get_source_content_hash(entry.id)
    existing_chunks = vector_store.count_for_source(entry.id)
    if not force and existing_hash == fetch.content_hash and existing_chunks > 0:
        return SourceRunResult(
            source_id=entry.id,
            url=entry.url,
            doc_type=entry.doc_type,
            scheme_id=entry.scheme_id,
            status="skipped",
            content_hash=fetch.content_hash,
            chunks=0,
            skipped=True,
        )

    texts = [chunk.text for chunk in chunks]
    embeddings = embedder.embed_documents(texts)
    stored = vector_store.replace_source_chunks(entry.id, chunks, embeddings)

    return SourceRunResult(
        source_id=entry.id,
        url=entry.url,
        doc_type=entry.doc_type,
        scheme_id=entry.scheme_id,
        status="indexed",
        content_hash=fetch.content_hash,
        chunks=stored,
        parse_warnings=parsed.parse_warnings,
    )


def _write_run_manifest(report: IngestRunReport) -> Path:
    directory = PROJECT_ROOT / "corpus" / "manifests"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.run_id}.json"
    body = json.dumps(report.to_dict(), indent=2)
    path.write_text(body, encoding="utf-8")

    # Persist on the Chroma volume so /corpus-status survives deploys (Railway Option A).
    if not report.dry_run:
        settings = get_settings()
        volume_dir = settings.vector_db_path.parent
        volume_dir.mkdir(parents=True, exist_ok=True)
        last_ingest = volume_dir / "last_ingest.json"
        summary = {
            "run_id": report.run_id,
            "finished_at": report.finished_at,
            "sources_processed": report.sources_processed,
            "sources_failed": report.sources_failed,
            "sources_skipped": report.sources_skipped,
            "total_chunks": report.total_chunks,
            "manifest_path": str(path),
        }
        last_ingest.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return path


def format_dry_run_summary(report: IngestRunReport) -> str:
    lines = [
        f"Ingest dry-run ({report.run_id})",
        f"Sources: {report.sources_processed} | Chunks: {report.total_chunks} | Failed: {report.sources_failed}",
        "",
        "Chunks by scheme:",
    ]
    for scheme_id, count in report.chunks_by_scheme.items():
        label = scheme_id if scheme_id != "_shared" else "(shared)"
        lines.append(f"  {label}: {count}")
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"  - {error}" for error in report.errors)
    return "\n".join(lines)
