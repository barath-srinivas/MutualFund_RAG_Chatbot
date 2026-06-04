from __future__ import annotations

import re
from enum import Enum

_FEES = re.compile(
    r"expense\s+ratio|exit\s+load|\bter\b|fees?|charges|load\s+structure|minimum\s+(?:sip|investment|lump\s*sum)",
    re.IGNORECASE,
)
_FUND_MGMT = re.compile(
    r"fund\s+manag|who\s+manages|investment\s+manager|portfolio\s+manager|managed\s+by|investment\s+team",
    re.IGNORECASE,
)
_BENCHMARK = re.compile(
    r"benchmark|riskometer|risk\s+meter",
    re.IGNORECASE,
)
_HOLDINGS = re.compile(
    r"\b(companies|holdings|portfolio|constituents?|stocks?\s+in|top\s+holdings?|sector\s+allocation)\b",
    re.IGNORECASE,
)
_OPERATIONAL = re.compile(
    r"download|statement|capital\s+gains|account\s+statement|how\s+to\s+(?:get|download|obtain)",
    re.IGNORECASE,
)


class QueryIntent(str, Enum):
    FEES = "fees"
    FUND_MANAGEMENT = "fund_management"
    BENCHMARK = "benchmark"
    HOLDINGS = "holdings"
    OPERATIONAL = "operational"
    GENERAL = "general"


def detect_intent(query: str) -> QueryIntent:
    if _OPERATIONAL.search(query):
        return QueryIntent.OPERATIONAL
    if _HOLDINGS.search(query):
        return QueryIntent.HOLDINGS
    if _FUND_MGMT.search(query):
        return QueryIntent.FUND_MANAGEMENT
    if _FEES.search(query):
        return QueryIntent.FEES
    if _BENCHMARK.search(query):
        return QueryIntent.BENCHMARK
    return QueryIntent.GENERAL


def preferred_doc_types(intent: QueryIntent) -> set[str]:
    if intent == QueryIntent.FEES:
        return {"kim", "factsheet", "sid"}
    if intent == QueryIntent.FUND_MANAGEMENT:
        return {"amc_product_page", "amc_scheme", "factsheet", "kim"}
    if intent == QueryIntent.HOLDINGS:
        return {"amc_product_page", "factsheet", "kim"}
    if intent == QueryIntent.BENCHMARK:
        return {"factsheet", "kim", "sid"}
    if intent == QueryIntent.OPERATIONAL:
        return {"amc_faq", "amfi", "sebi"}
    return set()


def preferred_topic(intent: QueryIntent) -> str | None:
    if intent == QueryIntent.FUND_MANAGEMENT:
        return "fund_management"
    if intent == QueryIntent.FEES:
        return "fees"
    if intent == QueryIntent.BENCHMARK:
        return "benchmark"
    return None
