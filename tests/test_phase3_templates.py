from __future__ import annotations

from datetime import date

from src.config.settings import get_settings
from src.guardrails.templates import advisory_refusal, out_of_scope_refusal, performance_template
from src.ingest.fetcher import is_url_allowed
from src.schemes.registry import get_scheme_registry


def test_advisory_template_has_one_allowlisted_url() -> None:
    today = date(2026, 6, 1)
    payload = advisory_refusal(today=today)
    assert payload["type"] == "refusal"
    assert payload["refusal_reason"] == "advisory"
    answer = str(payload["answer"])
    assert "http" not in answer
    assert payload["citation_url"] is not None
    assert is_url_allowed(str(payload["citation_url"]), get_settings().allowed_domain_list())


def test_out_of_scope_template_has_one_allowlisted_url() -> None:
    today = date(2026, 6, 1)
    payload = out_of_scope_refusal(today=today, registry=get_scheme_registry())
    assert payload["type"] == "refusal"
    assert payload["refusal_reason"] == "out_of_scope"
    answer = str(payload["answer"])
    assert "http" not in answer
    assert payload["citation_url"] is not None
    assert is_url_allowed(str(payload["citation_url"]), get_settings().allowed_domain_list())


def test_performance_template_has_one_url() -> None:
    today = date(2026, 6, 1)
    payload = performance_template(today=today, factsheet_url="https://www.icicipruamc.com/factsheet")
    assert payload["type"] == "refusal"
    assert payload["refusal_reason"] == "performance"
    assert "http" not in str(payload["answer"])
    assert payload["citation_url"] == "https://www.icicipruamc.com/factsheet"

