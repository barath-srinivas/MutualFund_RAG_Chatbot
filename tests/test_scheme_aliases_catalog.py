"""Sanity: every in-scope scheme has aliases and a distinct canonical citation URL."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from src.ingest.manifest import load_manifest
from src.schemes.registry import get_scheme_registry
from src.config.settings import get_settings
from tests.scheme_test_data import ALL_SCHEMES_INFORMAL


def test_each_scheme_has_at_least_two_aliases() -> None:
    get_scheme_registry.cache_clear()
    get_settings.cache_clear()
    registry = get_scheme_registry()
    schemes_path = Path(__file__).resolve().parents[1] / "corpus" / "schemes.yaml"
    data = yaml.safe_load(schemes_path.read_text(encoding="utf-8")) or {}
    for entry in data.get("schemes") or []:
        aliases = entry.get("aliases") or []
        assert len(aliases) >= 2, f"{entry['scheme_id']} needs aliases in schemes.yaml"


def test_canonical_urls_unique_across_ten_schemes() -> None:
    manifest = load_manifest()
    registry = get_scheme_registry()
    urls: list[str] = []
    for scheme in registry.list_schemes():
        url = manifest.factsheet_url_for_scheme(scheme.scheme_id)
        assert url and "icicipruamc.com" in url
        urls.append(url)
    assert len(urls) == len(set(urls))


@pytest.mark.parametrize(
    ("scheme_id", "phrase", "_url"),
    ALL_SCHEMES_INFORMAL,
)
def test_each_scheme_informal_phrase_resolves_from_registry(
    scheme_id: str, phrase: str, _url: str
) -> None:
    get_scheme_registry.cache_clear()
    get_settings.cache_clear()
    registry = get_scheme_registry()
    assert (
        registry.resolve_scheme_id(f"TER for {phrase}?") == scheme_id
    ), f"phrase {phrase!r} should map to {scheme_id}"


def test_scheme_aliases_doc_lists_all_scheme_ids() -> None:
    doc = (Path(__file__).resolve().parents[1] / "docs" / "scheme-aliases.md").read_text(
        encoding="utf-8"
    )
    registry = get_scheme_registry()
    for scheme in registry.list_schemes():
        assert re.search(rf"`{re.escape(scheme.scheme_id)}`", doc), (
            f"{scheme.scheme_id} missing from docs/scheme-aliases.md"
        )
