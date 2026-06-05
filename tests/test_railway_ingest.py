from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import get_settings
from src.ingest.pipeline import IngestRunReport


@pytest.fixture
def ingest_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("ENABLE_INTERNAL_INGEST", "true")
    monkeypatch.setenv("INGEST_TRIGGER_SECRET", "test-secret")
    monkeypatch.setenv("VECTOR_DB_PATH", str(tmp_path / "chroma"))
    get_settings.cache_clear()
    return TestClient(create_app())


def test_internal_ingest_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_INTERNAL_INGEST", "false")
    get_settings.cache_clear()
    client = TestClient(create_app())
    resp = client.post("/internal/ingest", headers={"Authorization": "Bearer x"})
    assert resp.status_code == 404


def test_internal_ingest_requires_secret(ingest_client: TestClient) -> None:
    resp = ingest_client.post("/internal/ingest")
    assert resp.status_code == 401


def test_internal_ingest_starts_background_job(ingest_client: TestClient) -> None:
    with patch("src.api.internal_ingest.threading.Thread") as mock_thread:
        resp = ingest_client.post(
            "/internal/ingest",
            headers={"Authorization": "Bearer test-secret"},
        )
    assert resp.status_code == 202
    assert resp.json()["status"] == "accepted"
    mock_thread.assert_called_once()


def test_internal_ingest_worker_runs_pipeline() -> None:
    report = IngestRunReport(
        run_id="ingest_test",
        started_at="2026-06-01T00:00:00+00:00",
        finished_at="2026-06-01T00:01:00+00:00",
        dry_run=False,
        manifest_path="corpus/urls.yaml",
        embedding_model="test",
        vector_db_path="data/chroma",
        sources_processed=1,
        sources_failed=0,
        sources_skipped=0,
        total_chunks=5,
        chunks_by_scheme={"icici-large-cap": 5},
    )
    with patch("src.api.internal_ingest.run_ingest", return_value=report) as mock_run:
        from src.api import internal_ingest as mod

        mod._running = True
        try:
            mod._ingest_worker(force=True)
        finally:
            mod._running = False
    assert mod._running is False
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs.get("force") is True


def test_corpus_status_reads_last_ingest(ingest_client: TestClient, tmp_path: Path) -> None:
    settings = get_settings()
    summary = {"run_id": "ingest_test", "finished_at": "2026-06-01T00:01:00+00:00", "total_chunks": 10}
    last_path = settings.vector_db_path.parent / "last_ingest.json"
    last_path.parent.mkdir(parents=True, exist_ok=True)
    last_path.write_text(json.dumps(summary), encoding="utf-8")

    with patch("src.api.corpus_status.ChromaVectorStore") as mock_store:
        mock_store.return_value.count.return_value = 42
        resp = ingest_client.get("/corpus-status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_count"] == 42
    assert body["last_ingest"]["run_id"] == "ingest_test"
