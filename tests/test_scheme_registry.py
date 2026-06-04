import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.config.settings import get_settings
from src.retrieval.preprocessor import resolve_scheme_id
from src.schemes.registry import SchemeRegistry, get_scheme_registry


@pytest.fixture
def registry() -> SchemeRegistry:
    get_scheme_registry.cache_clear()
    get_settings.cache_clear()
    return get_scheme_registry()


@pytest.fixture
def client() -> TestClient:
    get_scheme_registry.cache_clear()
    get_settings.cache_clear()
    return TestClient(create_app())


def test_registry_loads_ten_schemes(registry: SchemeRegistry) -> None:
    schemes = registry.list_schemes()
    assert len(schemes) == 10
    assert registry.amc == "ICICI Prudential Mutual Fund"


@pytest.mark.parametrize(
    "scheme_id",
    [
        "icici-large-cap",
        "icici-manufacturing",
        "icici-phd",
        "icici-us-bluechip",
        "icici-multi-asset",
        "icici-nifty-auto",
        "icici-nifty-50",
        "icici-nifty-500",
        "icici-nifty-bank",
        "icici-nifty-smallcap-250",
    ],
)
def test_get_scheme_by_id(registry: SchemeRegistry, scheme_id: str) -> None:
    scheme = registry.get(scheme_id)
    assert scheme is not None
    assert scheme.scheme_id == scheme_id


def test_resolve_multi_asset_alias(registry: SchemeRegistry) -> None:
    assert registry.resolve_scheme_id("What is the expense ratio for Multi Asset?") == "icici-multi-asset"


def test_resolve_dynamic_plan_slug(registry: SchemeRegistry) -> None:
    query = "icici-prudential-dynamic-plan-direct-growth exit load"
    assert registry.resolve_scheme_id(query) == "icici-multi-asset"


def test_resolve_manufacturing_alias(registry: SchemeRegistry) -> None:
    assert registry.resolve_scheme_id("Manufacturing fund NAV") == "icici-manufacturing"


def test_resolve_phd_alias(registry: SchemeRegistry) -> None:
    assert registry.resolve_scheme_id("PHD fund benchmark") == "icici-phd"


def test_resolve_nifty_500_before_nifty_50(registry: SchemeRegistry) -> None:
    assert registry.resolve_scheme_id("Nifty 500 Index expense ratio") == "icici-nifty-500"
    assert registry.resolve_scheme_id("Nifty 50 Index minimum SIP") == "icici-nifty-50"


def test_nifty_50_does_not_match_nifty_500_substring(registry: SchemeRegistry) -> None:
    assert registry.resolve_scheme_id("fund managers of nifty 500") == "icici-nifty-500"


@pytest.mark.parametrize(
    ("phrase", "expected_id"),
    [
        ("large cap", "icici-large-cap"),
        ("manufacturing", "icici-manufacturing"),
        ("pharma fund", "icici-phd"),
        ("us bluechip", "icici-us-bluechip"),
        ("multi asset", "icici-multi-asset"),
        ("auto index", "icici-nifty-auto"),
        ("nifty 50", "icici-nifty-50"),
        ("nifty 500", "icici-nifty-500"),
        ("bank index", "icici-nifty-bank"),
        ("smallcap 250", "icici-nifty-smallcap-250"),
        ("nifty smallcap", "icici-nifty-smallcap-250"),
    ],
)
def test_informal_aliases_resolve(
    registry: SchemeRegistry, phrase: str, expected_id: str
) -> None:
    assert registry.resolve_scheme_id(f"TER for {phrase}?") == expected_id


def test_resolve_bank_index_aliases(registry: SchemeRegistry) -> None:
    assert (
        registry.resolve_scheme_id("which are the top holdings in bank index?")
        == "icici-nifty-bank"
    )
    assert registry.resolve_scheme_id("Nifty Bank TER") == "icici-nifty-bank"


def test_bank_index_in_message_overrides_stale_sidebar(registry: SchemeRegistry) -> None:
    sid = resolve_scheme_id(
        "which are the top holdings in bank index?",
        explicit_scheme_id="icici-large-cap",
        registry=registry,
    )
    assert sid == "icici-nifty-bank"


def test_resolve_unknown_returns_none(registry: SchemeRegistry) -> None:
    assert registry.resolve_scheme_id("HDFC Top 100 fund") is None


def test_is_valid_scheme_id(registry: SchemeRegistry) -> None:
    assert registry.is_valid_scheme_id("icici-nifty-bank") is True
    assert registry.is_valid_scheme_id("hdfc-flexicap") is False


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_allowed_domains_from_settings() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    domains = settings.allowed_domain_list()
    assert "icicipruamc.com" in domains
    assert "amfiindia.com" in domains
    assert "sebi.gov.in" in domains


def test_embedding_defaults_to_local_bge_small() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.embedding_provider == "local"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.embedding_dimensions == 384
