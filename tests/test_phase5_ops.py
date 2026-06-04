from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.chat import ChatService
from src.api.rate_limit import SlidingWindowRateLimiter
from src.config.settings import get_settings
from src.observability.metrics import ChatMetrics
from src.schemes.registry import get_scheme_registry
from tests.eval.scoring import score_factual_response, score_refusal_response
from tests.test_phase2_chat_api import FakeLlm, FakeRetriever


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MINUTE", "1000")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        registry = app.state.scheme_registry
        app.state.chat_service = ChatService(
            registry=registry,
            retriever=FakeRetriever(),
            llm=FakeLlm(),
        )
        yield test_client


def test_metrics_endpoint_returns_snapshot(client: TestClient) -> None:
    client.post("/chat", json={"message": "Expense ratio?", "scheme_id": "icici-large-cap"})
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_requests"] >= 1
    assert "latency_p95_ms" in body
    assert "retrieval_hit_rate" in body


def test_rate_limiter_blocks_excess_requests() -> None:
    limiter = SlidingWindowRateLimiter(requests_per_minute=2)
    assert limiter.allow("test-client")
    assert limiter.allow("test-client")
    assert not limiter.allow("test-client")
    assert limiter.retry_after_seconds("test-client") >= 1


def test_chat_records_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    metrics = ChatMetrics()
    monkeypatch.setattr("src.observability.metrics._metrics", metrics)

    service = ChatService(
        registry=get_scheme_registry(),
        retriever=FakeRetriever(),
        llm=FakeLlm(),
    )
    service.chat(message="Expense ratio of Large Cap?", explicit_scheme_id="icici-large-cap")

    snap = metrics.snapshot()
    assert snap["total_requests"] == 1
    assert snap["answers"] == 1


def test_golden_factual_has_fifty_plus_cases() -> None:
    path = Path(__file__).parent / "eval" / "golden_factual.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert len(data["cases"]) >= 50


def test_scoring_accepts_valid_factual_answer() -> None:
    case = {"id": "x", "scheme_id": "icici-large-cap", "expected_topic": "fees"}
    response = {
        "type": "answer",
        "answer": "Expense ratio is 0.85%. Last updated from sources: 2026-05-31",
        "citation_url": "https://www.icicipruamc.com/mutual-fund/equity-funds/large-cap-fund",
    }
    result = score_factual_response(case, response)
    assert result.passed


def test_scoring_rejects_refusal_without_citation() -> None:
    case = {"id": "x", "expected_refusal_reason": "advisory"}
    response = {
        "type": "refusal",
        "refusal_reason": "advisory",
        "answer": "No advice. Last updated from sources: 2026-06-01",
        "citation_url": None,
    }
    result = score_refusal_response(case, response)
    assert not result.passed


def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as limited:
        limited.app.state.chat_service = ChatService(
            registry=get_scheme_registry(),
            retriever=FakeRetriever(),
            llm=FakeLlm(),
        )
        limited.post("/chat", json={"message": "a", "scheme_id": "icici-large-cap"})
        limited.post("/chat", json={"message": "b", "scheme_id": "icici-large-cap"})
        resp = limited.post("/chat", json={"message": "c", "scheme_id": "icici-large-cap"})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
