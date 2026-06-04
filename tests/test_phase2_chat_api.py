from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.chat import ChatService
from src.retrieval.models import RetrievedChunk


class FakeRetriever:
    def retrieve(self, *, message: str, scheme_id: str | None):
        chunk = RetrievedChunk(
            chunk_id="c1",
            text="Expense ratio (Direct): 0.85%.",
            score=0.9,
            scheme_id=scheme_id,
            doc_type="factsheet",
            source_url="https://www.icicipruamc.com/test",
            section="Fees",
            topic="fees",
            fetched_at=datetime(2026, 5, 31, tzinfo=timezone.utc),
        )

        from src.retrieval.models import RetrievalResult
        from src.retrieval.assembler import assemble_context

        result = RetrievalResult(chunks=[chunk], best_score=0.9, low_confidence=False)
        context = assemble_context([chunk])
        return result, context

    def factsheet_fallback_url(self, scheme_id: str | None):
        return "https://www.icicipruamc.com/factsheet"


class FakeLlm:
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return (
            "The expense ratio for the direct plan is 0.85%. "
            "https://www.icicipruamc.com/test "
            "Last updated from sources: 2026-05-31"
        )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        registry = app.state.scheme_registry
        app.state.chat_service = ChatService(registry=registry, retriever=FakeRetriever(), llm=FakeLlm())  # type: ignore[arg-type]
        yield test_client


def test_chat_endpoint_returns_structured_answer(client: TestClient) -> None:
    resp = client.post("/chat", json={"message": "Expense ratio of Large Cap?", "scheme_id": "icici-large-cap"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["type"] == "answer"
    assert "expense ratio" in payload["answer"].lower()
    assert payload["citation_url"].startswith("https://")
    assert payload["last_updated"] == "2026-05-31"

