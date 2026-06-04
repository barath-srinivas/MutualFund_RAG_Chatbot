from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.ingest.embedder import BGE_QUERY_PREFIX, LocalBgeEmbedder
from src.ingest.models import DocumentChunk
from src.ingest.pipeline import format_dry_run_summary, run_ingest
from src.ingest.vector_store import ChromaVectorStore

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _sample_chunk(source_id: str = "test-source", text: str = "Expense ratio 1.05%") -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"{source_id}:0000:abc",
        scheme_id="icici-large-cap",
        doc_type="factsheet",
        source_url="https://www.icicipruamc.com/test",
        source_id=source_id,
        section="Fees",
        topic="fees",
        fetched_at=datetime(2026, 5, 31, tzinfo=timezone.utc),
        text_hash="hash123",
        content_hash="content123",
        text=text,
    )


class FakeEmbedder:
    model_name = "test-embedder"
    dimensions = 384

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(index) / 100.0] * 384 for index, _ in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [0.5] * 384


class FakeVectorStore:
    def __init__(self) -> None:
        self._by_source: dict[str, list[tuple[DocumentChunk, list[float]]]] = {}
        self._content_hash: dict[str, str] = {}

    def count(self) -> int:
        return sum(len(items) for items in self._by_source.values())

    def get_source_content_hash(self, source_id: str) -> str | None:
        return self._content_hash.get(source_id)

    def count_for_source(self, source_id: str) -> int:
        return len(self._by_source.get(source_id, []))

    def delete_source(self, source_id: str) -> int:
        removed = len(self._by_source.pop(source_id, []))
        self._content_hash.pop(source_id, None)
        return removed

    def upsert_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0
        source_id = chunks[0].source_id
        self._by_source[source_id] = list(zip(chunks, embeddings, strict=True))
        self._content_hash[source_id] = chunks[0].content_hash
        return len(chunks)

    def replace_source_chunks(
        self,
        source_id: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> int:
        self.delete_source(source_id)
        return self.upsert_chunks(chunks, embeddings)


def test_local_embedder_uses_bge_query_prefix() -> None:
    embedder = LocalBgeEmbedder(model_name="BAAI/bge-small-en-v1.5")
    mock_model = MagicMock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]
    embedder._model = mock_model

    vector = embedder.embed_query("expense ratio")

    mock_model.encode.assert_called_once()
    assert mock_model.encode.call_args.args[0].startswith(BGE_QUERY_PREFIX)
    assert vector == [0.1, 0.2, 0.3]


@patch.object(ChromaVectorStore, "_connect")
def test_chroma_upsert_and_replace(mock_connect: MagicMock, tmp_path: Path) -> None:
    collection = MagicMock()
    mock_connect.return_value = collection

    store = ChromaVectorStore(path=tmp_path / "chroma", embedding_model="test-model")
    chunk = _sample_chunk()
    embedding = [0.1] * 384

    collection.get.return_value = {"ids": [], "metadatas": []}
    assert store.upsert_chunks([chunk], [embedding]) == 1
    collection.upsert.assert_called_once()

    collection.get.return_value = {
        "ids": [chunk.chunk_id],
        "metadatas": [{"content_hash": "content123"}],
    }
    assert store.get_source_content_hash("test-source") == "content123"

    updated = DocumentChunk(
        chunk_id="test-source:0000:def",
        scheme_id=chunk.scheme_id,
        doc_type=chunk.doc_type,
        source_url=chunk.source_url,
        source_id=chunk.source_id,
        section=chunk.section,
        topic=chunk.topic,
        fetched_at=chunk.fetched_at,
        text_hash="newhash",
        content_hash="content456",
        text="Expense ratio 1.10%",
    )
    store.replace_source_chunks("test-source", [updated], [embedding])
    collection.delete.assert_called_once()
    assert collection.upsert.call_count == 2


def test_run_ingest_dry_run_two_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = (FIXTURES / "sample_factsheet.html").read_bytes()
    urls = {
        "https://www.icicipruamc.com/a": html,
        "https://www.icicipruamc.com/b": html,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=urls[str(request.url)], headers={"Content-Type": "text/html"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    from src.ingest import fetcher as fetcher_module

    original_init = fetcher_module.DocumentFetcher.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["client"] = client
        kwargs["rate_limit_seconds"] = 0
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(fetcher_module.DocumentFetcher, "__init__", patched_init)

    manifest_path = tmp_path / "urls.yaml"
    manifest_path.write_text(
        """
version: 1
amc: Test
factsheet_canonical: {}
shared_sources: []
sources:
  - id: src-a
    url: https://www.icicipruamc.com/a
    doc_type: amc_scheme
    scheme_id: icici-large-cap
  - id: src-b
    url: https://www.icicipruamc.com/b
    doc_type: amc_scheme
    scheme_id: icici-manufacturing
""".strip(),
        encoding="utf-8",
    )

    report = run_ingest(manifest_path=manifest_path, dry_run=True, save_raw=False)

    assert report.dry_run is True
    assert report.total_chunks >= 2
    assert report.chunks_by_scheme["icici-large-cap"] >= 1
    assert report.chunks_by_scheme["icici-manufacturing"] >= 1
    assert report.sources_failed == 0
    summary = format_dry_run_summary(report)
    assert "Chunks by scheme" in summary


def test_run_ingest_indexes_with_fake_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = (FIXTURES / "sample_factsheet.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html, headers={"Content-Type": "text/html"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    from src.ingest import fetcher as fetcher_module

    original_init = fetcher_module.DocumentFetcher.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["client"] = client
        kwargs["rate_limit_seconds"] = 0
        kwargs["raw_dir"] = tmp_path / "raw"
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(fetcher_module.DocumentFetcher, "__init__", patched_init)

    manifest_path = tmp_path / "urls.yaml"
    manifest_path.write_text(
        """
version: 1
amc: Test
factsheet_canonical: {}
shared_sources: []
sources:
  - id: src-index
    url: https://www.icicipruamc.com/index
    doc_type: amc_scheme
    scheme_id: icici-large-cap
""".strip(),
        encoding="utf-8",
    )

    store = FakeVectorStore()
    report = run_ingest(
        manifest_path=manifest_path,
        dry_run=False,
        save_raw=False,
        embedder=FakeEmbedder(),
        vector_store=store,
    )

    assert report.sources_failed == 0
    assert report.total_chunks >= 1
    assert store.count() >= 1

    second = run_ingest(
        manifest_path=manifest_path,
        dry_run=False,
        save_raw=False,
        embedder=FakeEmbedder(),
        vector_store=store,
    )
    assert second.sources_skipped == 1
    assert second.total_chunks == 0


def test_run_ingest_writes_manifest_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = (FIXTURES / "sample_factsheet.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html, headers={"Content-Type": "text/html"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    from src.ingest import fetcher as fetcher_module
    from src.ingest import pipeline as pipeline_module

    original_init = fetcher_module.DocumentFetcher.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["client"] = client
        kwargs["rate_limit_seconds"] = 0
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(fetcher_module.DocumentFetcher, "__init__", patched_init)
    monkeypatch.setattr(pipeline_module, "PROJECT_ROOT", tmp_path)

    manifest_path = tmp_path / "corpus" / "urls.yaml"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        """
version: 1
amc: Test
factsheet_canonical: {}
shared_sources: []
sources:
  - id: src-one
    url: https://www.icicipruamc.com/one
    doc_type: amc_scheme
    scheme_id: icici-large-cap
""".strip(),
        encoding="utf-8",
    )

    report = run_ingest(
        manifest_path=manifest_path,
        dry_run=True,
        save_raw=False,
    )

    manifest_file = tmp_path / "corpus" / "manifests" / f"{report.run_id}.json"
    assert manifest_file.is_file()
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["total_chunks"] >= 1
    assert payload["sources"][0]["source_id"] == "src-one"
