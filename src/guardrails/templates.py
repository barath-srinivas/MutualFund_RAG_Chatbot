from __future__ import annotations

from datetime import date

from src.ingest.manifest import load_manifest
from src.schemes.registry import SchemeRegistry


def advisory_refusal(*, today: date) -> dict[str, str | None]:
    citation = _amfi_or_sebi_link()
    answer = (
        "I can only provide factual information from official AMC/AMFI/SEBI sources and cannot give "
        "investment advice or comparisons. Please use the official source link below. "
        f"Last updated from sources: {today.isoformat()}"
    )
    return {
        "answer": answer,
        "citation_url": citation,
        "last_updated": today.isoformat(),
        "type": "refusal",
        "refusal_reason": "advisory",
        "structured": None,
    }


def out_of_scope_refusal(*, today: date, registry: SchemeRegistry) -> dict[str, str | None]:
    citation = _amfi_or_sebi_link()
    names = ", ".join(s.display_name for s in registry.list_schemes()[:3])
    answer = (
        "I currently cover only 10 ICICI Prudential direct-growth schemes in this assistant and cannot answer for "
        f"other funds/AMCs. Example in-scope schemes include: {names}. "
        "Please use the official source link below. "
        f"Last updated from sources: {today.isoformat()}"
    )
    return {
        "answer": answer,
        "citation_url": citation,
        "last_updated": today.isoformat(),
        "type": "refusal",
        "refusal_reason": "out_of_scope",
        "structured": None,
    }


def performance_template(*, today: date, factsheet_url: str | None) -> dict[str, str | None]:
    citation = factsheet_url or _amfi_or_sebi_link()
    answer = (
        "I cannot provide performance calculations or return comparisons. "
        "For official performance details, please use the official source link below. "
        f"Last updated from sources: {today.isoformat()}"
    )
    return {
        "answer": answer,
        "citation_url": citation,
        "last_updated": today.isoformat(),
        "type": "refusal",
        "refusal_reason": "performance",
        "structured": None,
    }


def pii_refusal(*, today: date) -> dict[str, str | None]:
    answer = (
        "I cannot help with requests that include personal identifiers like PAN, Aadhaar, account numbers, "
        "phone numbers, emails, or OTPs. Please remove personal data and ask again. "
        f"Last updated from sources: {today.isoformat()}"
    )
    return {
        "answer": answer,
        "citation_url": None,
        "last_updated": today.isoformat(),
        "type": "refusal",
        "refusal_reason": "pii",
        "structured": None,
    }


def _amfi_or_sebi_link() -> str:
    manifest = load_manifest()
    for entry in manifest.shared_sources:
        if entry.doc_type in {"amfi", "sebi"} and entry.allowed_for_citation:
            return entry.url
    return "https://www.amfiindia.com/"

