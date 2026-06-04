"""Fetch ICICI AMC React product pages via Playwright (SPA + apimf API)."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_FUND_ID_RE = re.compile(r"/(\d+)/?$")
_FUND_DETAILS_RE = re.compile(r"/fs/v1/funds/(\d+)/details$")
_SCHEME_API_RE = re.compile(r"/fs/v1/funds/(\d+)/")

# Tabs on AMC product pages (Portfolio / More Details sections).
_INTERACTIVE_TABS = (
    "Holdings",
    "Fund Manager",
    "Sectors",
)

API_BASE = "https://apimf.icicipruamc.com"


@dataclass
class AmcSpaPayload:
    page_url: str
    fund_id: str
    scheme_code: str | None
    page_text: str
    fund_api: dict[str, Any] | None
    tab_sections: dict[str, str] = field(default_factory=dict)
    extra_apis: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_bytes(self) -> bytes:
        """Serialize for fetch content + content-hash."""
        return json.dumps(
            {
                "page_url": self.page_url,
                "fund_id": self.fund_id,
                "scheme_code": self.scheme_code,
                "page_text": self.page_text,
                "fund_api": self.fund_api,
                "tab_sections": self.tab_sections,
                "extra_apis": self.extra_apis,
                "warnings": self.warnings,
            },
            ensure_ascii=False,
        ).encode("utf-8")


def extract_fund_id_from_url(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    match = _FUND_ID_RE.search(path)
    return match.group(1) if match else None


def resolve_direct_growth_scheme_code(fund_api: dict[str, Any] | None) -> str | None:
    """Pick schemeCode for Direct + Growth (or best Growth plan) from fund details API."""
    if not isinstance(fund_api, dict):
        return None
    data = fund_api.get("success", {}).get("data", fund_api.get("data", fund_api))
    if not isinstance(data, dict):
        return None
    schemes = data.get("schemes")
    if not isinstance(schemes, list) or not schemes:
        return None

    def score(scheme: dict[str, Any]) -> int:
        name = str(scheme.get("schemeName") or "").lower()
        option = str(scheme.get("schemeOption") or "").lower()
        plan = str(scheme.get("plan") or "").lower()
        points = 0
        if "direct" in name or plan == "direct":
            points += 10
        if option == "growth":
            points += 8
        if "idcw" in name or option == "idcw":
            points -= 20
        if "regular" in name and "direct" not in name and plan != "direct":
            points -= 5
        return points

    ranked = sorted(
        (s for s in schemes if isinstance(s, dict) and s.get("schemeCode")),
        key=score,
        reverse=True,
    )
    if not ranked:
        return None
    return str(ranked[0]["schemeCode"])


def fetch_amc_product_page(url: str, *, timeout_ms: int = 120_000) -> AmcSpaPayload:
    """Load AMC scheme page; capture APIs, tab panels (Holdings, Fund Manager), and visible text."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Playwright is required for amc_product_page sources. "
            "Install with: pip install playwright && playwright install chromium"
        ) from exc

    fund_id = extract_fund_id_from_url(url)
    if not fund_id:
        raise ValueError(f"Could not parse fund id from AMC product URL: {url}")

    fund_api: dict[str, Any] | None = None
    extra_apis: dict[str, Any] = {}
    warnings: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        def on_response(response) -> None:
            nonlocal fund_api
            req_url = response.url
            if "apimf.icicipruamc.com" not in req_url or response.status != 200:
                return
            try:
                if _FUND_DETAILS_RE.search(req_url):
                    match = _FUND_DETAILS_RE.search(req_url)
                    if match and match.group(1) == fund_id:
                        fund_api = response.json()
                elif "/portfolio?type=HL" in req_url:
                    extra_apis["portfolio_holdings"] = response.json()
                elif "/portfolio?type=ST" in req_url:
                    extra_apis["portfolio_sectors"] = response.json()
                elif "/metrics" in req_url and _SCHEME_API_RE.search(req_url):
                    extra_apis["metrics"] = response.json()
                elif "/performance" in req_url and _SCHEME_API_RE.search(req_url):
                    if "performance" not in extra_apis:
                        extra_apis["performance"] = response.json()
                elif "/managed-funds/" in req_url:
                    extra_apis.setdefault("fund_managers", []).append(response.json())
            except Exception as exc:
                warnings.append(f"API capture failed for {req_url}: {exc}")

        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_response(
                lambda r: bool(_FUND_DETAILS_RE.search(r.url)) and r.status == 200,
                timeout=60_000,
            )
        except Exception:
            warnings.append("Timed out waiting for fund details API response")
        page.wait_for_timeout(2000)

        _dismiss_overlays(page)
        tab_sections = _expand_product_tabs(page, warnings)

        if fund_api is None:
            fund_api = _fetch_json_via_request(
                page,
                f"{API_BASE}/fs/v1/funds/{fund_id}/details",
                warnings,
                label="fund details",
            )

        scheme_code = resolve_direct_growth_scheme_code(fund_api)
        if scheme_code:
            _fetch_scheme_apis_via_request(page, scheme_code, extra_apis, warnings)

        page_text = page.inner_text("body")
        browser.close()

    if not page_text.strip():
        warnings.append("Rendered page text is empty")
    if fund_api is None:
        warnings.append(f"Fund details API not captured for fund id {fund_id}")
    if not scheme_code:
        warnings.append("Could not resolve Direct Growth schemeCode from fund details")
    if "portfolio_holdings" not in extra_apis:
        warnings.append("Portfolio holdings API not captured")

    return AmcSpaPayload(
        page_url=url,
        fund_id=fund_id,
        scheme_code=scheme_code,
        page_text=page_text,
        fund_api=fund_api,
        tab_sections=tab_sections,
        extra_apis=extra_apis,
        warnings=warnings,
    )


def _expand_product_tabs(page: Any, warnings: list[str]) -> dict[str, str]:
    """Click Holdings / Fund Manager / Sectors and capture visible panel text."""
    sections: dict[str, str] = {}
    for label in _INTERACTIVE_TABS:
        try:
            control = page.get_by_role("tab", name=label)
            if control.count() == 0:
                control = page.get_by_text(label, exact=True)
            tab = control.first
            if not tab.is_visible(timeout=3000):
                continue
            tab.click(timeout=8000)
            page.wait_for_timeout(2000)
            snippet = _extract_fund_panel_text(page)
            if snippet.strip():
                sections[label] = snippet.strip()
        except Exception as exc:
            warnings.append(f"Tab {label!r} expand failed: {exc}")
    return sections


def _dismiss_overlays(page: Any) -> None:
    """Close MUI menus/backdrops that block tab clicks."""
    for _ in range(3):
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    try:
        backdrop = page.locator(".MuiBackdrop-root").first
        if backdrop.is_visible(timeout=500):
            backdrop.click(timeout=2000, force=True)
            page.wait_for_timeout(300)
    except Exception:
        pass


def _api_headers(page: Any) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Referer": page.url,
        "Origin": "https://www.icicipruamc.com",
    }


def _fetch_json_via_request(
    page: Any,
    url: str,
    warnings: list[str],
    *,
    label: str,
) -> dict[str, Any] | None:
    try:
        response = page.request.get(url, headers=_api_headers(page), timeout=30_000)
        if response.ok:
            return response.json()
        warnings.append(f"{label} API returned {response.status}")
    except Exception as exc:
        warnings.append(f"{label} API request failed: {exc}")
    return None


def _fetch_scheme_apis_via_request(
    page: Any,
    scheme_code: str,
    extra_apis: dict[str, Any],
    warnings: list[str],
) -> None:
    """Fetch portfolio/metrics JSON for the Direct Growth schemeCode via apimf."""
    endpoints = {
        "portfolio_holdings": f"{API_BASE}/fs/v1/funds/{scheme_code}/portfolio?type=HL",
        "portfolio_sectors": f"{API_BASE}/fs/v1/funds/{scheme_code}/portfolio?type=ST",
        "metrics": f"{API_BASE}/fs/v1/funds/{scheme_code}/metrics",
    }
    for key, url in endpoints.items():
        payload = _fetch_json_via_request(page, url, warnings, label=key)
        if payload is not None:
            extra_apis[key] = payload


def _extract_fund_panel_text(page: Any) -> str:
    """Prefer main fund content over site chrome."""
    for selector in ("main", "#root", "body"):
        try:
            loc = page.locator(selector).first
            if loc.count():
                return loc.inner_text(timeout=5000)
        except Exception:
            continue
    return page.inner_text("body")
