from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.chat import ChatService


class CountingRetriever:
    def __init__(self) -> None:
        self.calls = 0

    def retrieve(self, *, message: str, scheme_id: str | None):
        self.calls += 1
        return None, None

    def factsheet_fallback_url(self, scheme_id: str | None):
        return "https://www.icicipruamc.com/factsheet"


class DummyLlm:
    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        return "N/A"


def test_advisory_route_does_not_call_retriever() -> None:
    retriever = CountingRetriever()
    app = create_app()
    with TestClient(app) as client:
        registry = app.state.scheme_registry
        app.state.chat_service = ChatService(registry=registry, retriever=retriever, llm=DummyLlm())  # type: ignore[arg-type]
        resp = client.post("/chat", json={"message": "Should I invest in Technology fund?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["type"] == "refusal"
        assert payload["refusal_reason"] == "advisory"
        assert retriever.calls == 0


def test_performance_route_does_not_call_retriever() -> None:
    retriever = CountingRetriever()
    app = create_app()
    with TestClient(app) as client:
        registry = app.state.scheme_registry
        app.state.chat_service = ChatService(registry=registry, retriever=retriever, llm=DummyLlm())  # type: ignore[arg-type]
        resp = client.post("/chat", json={"message": "What was 5Y return of Large Cap?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["type"] == "refusal"
        assert payload["refusal_reason"] == "performance"
        assert retriever.calls == 0


def test_out_of_scope_route_does_not_call_retriever() -> None:
    retriever = CountingRetriever()
    app = create_app()
    with TestClient(app) as client:
        registry = app.state.scheme_registry
        app.state.chat_service = ChatService(registry=registry, retriever=retriever, llm=DummyLlm())  # type: ignore[arg-type]
        resp = client.post("/chat", json={"message": "HDFC Top 100 expense ratio?"})
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["type"] == "refusal"
        assert payload["refusal_reason"] == "out_of_scope"
        assert retriever.calls == 0

