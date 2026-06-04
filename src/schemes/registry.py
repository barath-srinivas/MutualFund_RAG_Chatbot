from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from src.config.settings import get_settings


class Scheme(BaseModel):
    scheme_id: str
    display_name: str
    category: str
    groww_slug: str = ""
    aliases: list[str] = Field(default_factory=list)


class SchemeRegistry:
    def __init__(self, schemes: list[Scheme], amc: str = "") -> None:
        self.amc = amc
        self._by_id: dict[str, Scheme] = {s.scheme_id: s for s in schemes}
        self._lookup: list[tuple[str, str]] = self._build_lookup(schemes)

    @classmethod
    def from_yaml(cls, path: Path) -> SchemeRegistry:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        schemes = [Scheme.model_validate(item) for item in data.get("schemes") or []]
        return cls(schemes=schemes, amc=data.get("amc") or "")

    def _build_lookup(self, schemes: list[Scheme]) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []
        for scheme in schemes:
            entries.append((self._normalize(scheme.scheme_id), scheme.scheme_id))
            entries.append((self._normalize(scheme.display_name), scheme.scheme_id))
            if scheme.groww_slug:
                entries.append((self._normalize(scheme.groww_slug), scheme.scheme_id))
                # slug without icici-prudential- prefix for partial mentions
                slug_tail = scheme.groww_slug.replace("icici-prudential-", "")
                entries.append((self._normalize(slug_tail), scheme.scheme_id))
            for alias in scheme.aliases:
                entries.append((self._normalize(alias), scheme.scheme_id))
        # Longer phrases first to prefer specific matches (e.g. Nifty Next 50 before Nifty 50)
        entries.sort(key=lambda item: len(item[0]), reverse=True)
        return entries

    @staticmethod
    def _normalize(text: str) -> str:
        lowered = text.lower().strip()
        lowered = re.sub(r"[^\w\s-]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def get(self, scheme_id: str) -> Scheme | None:
        return self._by_id.get(scheme_id)

    def list_schemes(self) -> list[Scheme]:
        return list(self._by_id.values())

    def resolve_scheme_id(self, text: str) -> str | None:
        """Match user text to a scheme_id using aliases, names, and Groww slugs.

        Alias list: corpus/schemes.yaml; formal spec: docs/scheme-aliases.md.
        """
        if not text or not text.strip():
            return None

        normalized_query = self._normalize(text)

        # Exact scheme_id in text
        for scheme_id in self._by_id:
            if self._normalize(scheme_id) == normalized_query:
                return scheme_id

        for phrase, scheme_id in self._lookup:
            if not phrase:
                continue
            if self._phrase_in_query(phrase, normalized_query):
                return scheme_id

        return None

    @staticmethod
    def _phrase_in_query(phrase: str, normalized_query: str) -> bool:
        """Match aliases with word boundaries so 'nifty 50' does not match 'nifty 500'."""
        if len(phrase) < 12:
            pattern = r"\b" + re.escape(phrase) + r"(?:\b|$)"
            return bool(re.search(pattern, normalized_query))
        return phrase in normalized_query

    def is_valid_scheme_id(self, scheme_id: str) -> bool:
        return scheme_id in self._by_id

    def search_phrases_for_scheme(self, scheme_id: str) -> list[str]:
        """Phrases likely to appear in corpus text for this scheme (for retrieval reranking)."""
        scheme = self._by_id.get(scheme_id)
        if scheme is None:
            return []
        phrases: list[str] = [scheme.display_name, *scheme.aliases]
        # Distinctive tail from display name, e.g. "Large Cap Fund"
        if "Fund" in scheme.display_name:
            tail = scheme.display_name.split("ICICI Prudential", 1)[-1].strip()
            if len(tail) > 8:
                phrases.append(tail)
        seen: set[str] = set()
        unique: list[str] = []
        for phrase in phrases:
            key = phrase.lower().strip()
            if key and key not in seen and len(key) > 4:
                seen.add(key)
                unique.append(phrase)
        return unique


@lru_cache
def get_scheme_registry() -> SchemeRegistry:
    settings = get_settings()
    path = settings.corpus_schemes_path
    if not path.is_file():
        raise FileNotFoundError(f"Scheme registry not found: {path}")
    return SchemeRegistry.from_yaml(path)
