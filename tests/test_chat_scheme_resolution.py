"""Integration: /chat uses message-resolved scheme for retrieval and citation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.chat import ChatService
from src.config.settings import get_settings
from src.ingest.manifest import load_manifest
from src.retrieval.assembler import assemble_context
from src.retrieval.models import RetrievedChunk, RetrievalResult
from src.schemes.registry import get_scheme_registry
from tests.scheme_test_data import ALL_SCHEMES_INFORMAL, STALE_PICKER_SCHEME_ID


class RecordingRetriever:
    def __init__(self) -> None:
        self.last_scheme_id: str | None = None

    def retrieve(self, *, message: str, scheme_id: str | None):
        self.last_scheme_id = scheme_id
        chunk = RetrievedChunk(
            chunk_id="c1",
            text="Expense ratio (Direct): 0.85%.",
            score=0.9,
            scheme_id=scheme_id,
            doc_type="amc_product_page",
            source_url="https://www.icicipruamc.com/placeholder",
            section="Fees",
            topic="fees",
            fetched_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        result = RetrievalResult(chunks=[chunk], best_score=0.9, low_confidence=False)
        return result, assemble_context([chunk])

    def factsheet_fallback_url(self, scheme_id: str | None):
        manifest = load_manifest()
        return manifest.factsheet_url_for_scheme(scheme_id) if scheme_id else None


class CleanLlm:
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return (
            "The direct plan expense ratio is 0.85%. "
            "Last updated from sources: 2026-06-01"
        )


@pytest.fixture
def client() -> TestClient:
    get_scheme_registry.cache_clear()
    get_settings.cache_clear()
    app = create_app()
    retriever = RecordingRetriever()
    with TestClient(app) as test_client:
        registry = app.state.scheme_registry
        app.state.chat_service = ChatService(
            registry=registry,
            retriever=retriever,  # type: ignore[arg-type]
            llm=CleanLlm(),  # type: ignore[arg-type]
        )
        test_client.app.state._test_retriever = retriever  # type: ignore[attr-defined]
        yield test_client


def test_chat_bank_index_message_overrides_large_cap_picker(client: TestClient) -> None:
    retriever: RecordingRetriever = client.app.state._test_retriever  # type: ignore[attr-defined]
    manifest = load_manifest()

    resp = client.post(
        "/chat",
        json={
            "message": "which are the top holdings in bank index?",
            "scheme_id": "icici-large-cap",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["type"] == "answer"
    assert retriever.last_scheme_id == "icici-nifty-bank"
    assert payload["citation_url"] == manifest.factsheet_url_for_scheme("icici-nifty-bank")
    assert "nifty-bank-index-fund" in payload["citation_url"]
    assert "large-cap-fund" not in payload["citation_url"]


@pytest.mark.parametrize(
    ("target_scheme_id", "phrase", "url_fragment"),
    ALL_SCHEMES_INFORMAL,
)
def test_chat_each_scheme_message_overrides_stale_picker(
    client: TestClient,
    target_scheme_id: str,
    phrase: str,
    url_fragment: str,
) -> None:
    retriever: RecordingRetriever = client.app.state._test_retriever  # type: ignore[attr-defined]
    manifest = load_manifest()
    stale = (
        "icici-nifty-bank"
        if target_scheme_id == STALE_PICKER_SCHEME_ID
        else STALE_PICKER_SCHEME_ID
    )

    resp = client.post(
        "/chat",
        json={
            "message": f"What is the expense ratio for {phrase}?",
            "scheme_id": stale,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["type"] == "answer"
    assert retriever.last_scheme_id == target_scheme_id
    assert payload["citation_url"] == manifest.factsheet_url_for_scheme(target_scheme_id)
    assert url_fragment in payload["citation_url"]


def test_chat_picker_used_when_message_unscoped(client: TestClient) -> None:
    retriever: RecordingRetriever = client.app.state._test_retriever  # type: ignore[attr-defined]
    manifest = load_manifest()

    resp = client.post(
        "/chat",
        json={"message": "What is the exit load?", "scheme_id": "icici-nifty-500"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert retriever.last_scheme_id == "icici-nifty-500"
    assert payload["citation_url"] == manifest.factsheet_url_for_scheme("icici-nifty-500")
