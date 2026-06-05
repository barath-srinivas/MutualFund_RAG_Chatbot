from __future__ import annotations

import re

# Section headings that receive topic=fund_management (task 1.10, architecture §5.2)
_FUND_MANAGEMENT_HEADING = re.compile(
    r"^(?:"
    r"fund\s+managers?"
    r"|investment\s+team"
    r"|fund\s+management"
    r"|portfolio\s+managers?"
    r"|investment\s+managers?"
    r"|scheme\s+managers?"
    r")(?:\s|$|[:\-–])",
    re.IGNORECASE,
)

# Index/passive funds often disclose mandate under these headings (coverage matrix IDX)
_INDEX_MANDATE_HEADING = re.compile(
    r"^(?:investment\s+objective|index\s+(?:fund\s+)?(?:details|information)|fund\s+overview)",
    re.IGNORECASE,
)
_INDEX_MANDATE_TEXT = re.compile(
    r"index(?:ed)?\s+(?:fund|replicat)|passive(?:ly)?\s+manag|track(?:ing|s)\s+(?:the\s+)?(?:index|nifty)",
    re.IGNORECASE,
)

_FEES = re.compile(
    r"expense\s+ratio|exit\s+load|\bter\b|fees?|charges|load\s+structure|minimum\s+(?:sip|investment)",
    re.IGNORECASE,
)
_BENCHMARK = re.compile(
    r"benchmark|riskometer|risk\s+meter",
    re.IGNORECASE,
)
_SECTION_PART_SUFFIX = re.compile(r"\s*\(part\s+\d+\)$", re.IGNORECASE)


def normalize_section_heading(section: str) -> str:
    """Strip chunker part suffixes so heading rules still apply."""
    return _SECTION_PART_SUFFIX.sub("", section).strip()


def is_fund_management_heading(section: str) -> bool:
    """True when section heading matches Fund Manager / Investment Team patterns."""
    heading = normalize_section_heading(section)
    if not heading:
        return False
    return bool(_FUND_MANAGEMENT_HEADING.match(heading))


def is_index_mandate_section(section: str, text: str) -> bool:
    """Tag passive/index mandate disclosures as fund_management for retrieval."""
    heading = normalize_section_heading(section)
    if _INDEX_MANDATE_HEADING.match(heading) and _INDEX_MANDATE_TEXT.search(text[:800]):
        return True
    return False


def tag_chunk_topic(
    *,
    section: str,
    text: str,
    manifest_topic: str | None = None,
) -> str | None:
    """
    Assign chunk topic metadata (task 1.10).

    fund_management is set from section headings (Fund Manager, Investment Team, etc.)
    or index-mandate sections for passive funds. Manifest topic overrides inference.
    """
    if manifest_topic:
        return manifest_topic

    heading = normalize_section_heading(section)

    if is_fund_management_heading(heading):
        return "fund_management"

    if is_index_mandate_section(heading, text):
        return "fund_management"

    combined = f"{heading}\n{text[:500]}"
    if _FEES.search(combined):
        return "fees"
    if _BENCHMARK.search(combined):
        return "benchmark"
    return None
