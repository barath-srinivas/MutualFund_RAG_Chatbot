"""Shared fixtures: one informal query phrase and canonical URL fragment per scheme."""

from __future__ import annotations

# (scheme_id, informal phrase in user message, unique substring of AMC product URL)
ALL_SCHEMES_INFORMAL: list[tuple[str, str, str]] = [
    ("icici-large-cap", "large cap", "large-cap-fund/211"),
    ("icici-manufacturing", "manufacturing", "manufacturing-fund/1657"),
    ("icici-phd", "pharma fund", "pharma-healthcare-and-diagnostics"),
    ("icici-us-bluechip", "us bluechip", "us-bluechip-equity-fund/437"),
    ("icici-multi-asset", "multi asset", "multi-asset-fund/55"),
    ("icici-nifty-auto", "auto index", "nifty-auto-index-fund/1851"),
    ("icici-nifty-50", "nifty 50", "nifty-50-index-fund/57"),
    ("icici-nifty-500", "nifty 500", "nifty-500-index-fund/1884"),
    ("icici-nifty-bank", "bank index", "nifty-bank-index-fund/1839"),
    ("icici-nifty-smallcap-250", "smallcap 250", "nifty-smallcap-250-index-fund/1828"),
]

# Stale sidebar selection used when testing message-over-picker (not the target fund).
STALE_PICKER_SCHEME_ID = "icici-large-cap"
