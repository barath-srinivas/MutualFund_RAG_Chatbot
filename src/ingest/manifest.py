from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from src.config.settings import PROJECT_ROOT, get_settings

DocType = Literal[
    "factsheet",
    "kim",
    "sid",
    "amc_scheme",
    "amc_product_page",
    "amc_faq",
    "amfi",
    "sebi",
]
TopicType = Literal["fund_management", "fees", "benchmark"] | None


class SourceEntry(BaseModel):
    """Single official URL in the corpus registry (task 1.5)."""

    id: str
    url: str
    doc_type: DocType
    scheme_id: str | None = None
    topic: str | None = None
    allowed_for_citation: bool = True
    notes: str | None = None

    @field_validator("scheme_id", mode="before")
    @classmethod
    def empty_scheme_to_none(cls, value: object) -> str | None:
        if value is None or value == "" or value == "null":
            return None
        return str(value)


class CorpusManifest(BaseModel):
    version: int = 1
    amc: str = ""
    factsheet_canonical: dict[str, str] = Field(default_factory=dict)
    shared_sources: list[SourceEntry] = Field(default_factory=list)
    sources: list[SourceEntry] = Field(default_factory=list)

    def all_sources(self) -> list[SourceEntry]:
        return list(self.shared_sources) + list(self.sources)

    def get_by_id(self, source_id: str) -> SourceEntry | None:
        for entry in self.all_sources():
            if entry.id == source_id:
                return entry
        return None

    def factsheet_url_for_scheme(self, scheme_id: str) -> str | None:
        return self.factsheet_canonical.get(scheme_id)


def load_manifest(path: Path | None = None) -> CorpusManifest:
    settings = get_settings()
    manifest_path = path or settings.corpus_urls_path
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Corpus manifest not found: {manifest_path}")

    with manifest_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return CorpusManifest.model_validate(data)


def default_manifest_path() -> Path:
    return PROJECT_ROOT / "corpus" / "urls.yaml"
