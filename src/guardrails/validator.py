from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from src.config.settings import get_settings
from src.ingest.fetcher import is_url_allowed
from src.retrieval.citations import is_public_citation_url

_URL_RE = re.compile(r"https?://[^\s)>\"]+")
_FOOTER_PREFIX = "Last updated from sources:"
# Do not treat honorific / common abbreviations as sentence boundaries (e.g. "Mr. Patel").
_ABBREV_WITH_PERIOD = re.compile(
    r"\b(?:Mr|Ms|Mrs|Dr|Prof|Sr|Jr|vs|etc|approx|No|Ltd|Inc)\.",
    re.IGNORECASE,
)
_SUBJECTIVE_MANAGER = re.compile(
    r"\b(good\s+manager|best\s+manager|better\s+manager|trust\s+the\s+manager|top\s+manager)\b",
    re.IGNORECASE,
)
_PERFORMANCE_NUMBER = re.compile(
    r"\b\d+(?:\.\d+)?\s*%\b|\b(?:1|3|5|10)\s*(?:year|yr|y)\s+return\b|\bcagr\b",
    re.IGNORECASE,
)
# LLM meta-commentary about retrieval/context (not user-facing facts).
_META_COMMENTARY = re.compile(
    r"\b(?:context|provided context|available in the (?:context|sources)|"
    r"this information is available|does not provide any additional|"
    r"no additional information|information (?:is|was) (?:not )?available in)\b",
    re.IGNORECASE,
)


@dataclass
class ValidationResult:
    answer: str
    citation_url: str
    last_updated: date | None


def validate_answer(
    draft: str,
    *,
    citation_url: str | None,
    last_updated: date | None,
    allow_performance_numbers: bool = False,
    max_sentences: int | None = None,
) -> ValidationResult:
    """
    Phase 2.7 validator v1 (standard factual answers):
    - <= max_sentences (default from settings, typically 3)
    - one allowlisted citation URL in citation_url (not embedded in answer body)
    - footer "Last updated from sources: YYYY-MM-DD"
    """
    settings = get_settings()
    allowed = settings.allowed_domain_list()
    sentence_cap = max_sentences if max_sentences is not None else settings.answer_max_sentences

    text = (draft or "").strip()
    text = _strip_subjective_manager_phrases(text)
    if not allow_performance_numbers:
        text = _strip_performance_numbers(text)
    urls = _URL_RE.findall(text)

    chosen = _choose_citation_url(urls, preferred=citation_url, allowed_domains=allowed)
    if not chosen:
        # Fail closed: if we cannot produce an allowlisted URL, return the preferred URL if allowlisted.
        if citation_url and is_public_citation_url(citation_url, allowed_domains=allowed):
            chosen = citation_url
        else:
            chosen = ""

    # Strip URLs from answer body; citation is returned separately for the UI link.
    text = _URL_RE.sub("", text)
    text = _clean_spaces(text)
    text = _strip_meta_commentary(text)
    if text and not text.endswith((".", "!", "?", ":")):
        text = text.rstrip() + "."

    text = _enforce_sentence_cap(text, max_sentences=sentence_cap)

    footer_date = last_updated or date.today()
    text = _ensure_footer(text, footer_date)

    # If the chosen URL is not allowlisted, blank it (caller should fall back).
    if chosen and not is_public_citation_url(chosen, allowed_domains=allowed):
        chosen = ""

    return ValidationResult(
        answer=text,
        citation_url=chosen,
        last_updated=footer_date,
    )


def _choose_citation_url(urls: list[str], *, preferred: str | None, allowed_domains: list[str]) -> str | None:
    if preferred and is_public_citation_url(preferred, allowed_domains=allowed_domains):
        return preferred
    for url in urls:
        if is_public_citation_url(url, allowed_domains=allowed_domains):
            return url
    return None


def _split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries without breaking Mr./Ms./Mrs. honorifics."""
    marked = _ABBREV_WITH_PERIOD.sub(
        lambda match: match.group(0).replace(".", "\u2024"),
        text.strip(),
    )
    parts = re.split(r"(?<=[.!?])\s+", marked)
    return [part.replace("\u2024", ".") for part in parts if part.strip()]


def _enforce_sentence_cap(text: str, *, max_sentences: int) -> str:
    parts = _split_sentences(text)
    if len(parts) <= max_sentences:
        return text.strip()
    return " ".join(parts[:max_sentences]).strip()


def _ensure_footer(text: str, footer_date: date) -> str:
    if _FOOTER_PREFIX.lower() in text.lower():
        return text.strip()
    suffix = f"{_FOOTER_PREFIX} {footer_date.isoformat()}"
    if not text.endswith((".", "!", "?")):
        text = text.rstrip() + "."
    return f"{text} {suffix}".strip()


def _clean_spaces(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\(\s+\)", "", cleaned)
    return cleaned.strip()


def _strip_subjective_manager_phrases(text: str) -> str:
    return _SUBJECTIVE_MANAGER.sub("manager", text)


def _strip_performance_numbers(text: str) -> str:
    return _PERFORMANCE_NUMBER.sub("", text)


def _strip_meta_commentary(text: str) -> str:
    """Drop sentences that discuss retrieval/context instead of fund facts."""
    parts = _split_sentences(text)
    if not parts:
        return text.strip()
    kept = [part for part in parts if not _META_COMMENTARY.search(part)]
    if not kept:
        return text.strip()
    return " ".join(kept).strip()

