"""One-off: save full fund-57 API JSON for test fixtures."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = (
    "https://www.icicipruamc.com/mutual-fund/index-funds/"
    "icici-prudential-nifty-50-index-fund/57"
)
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "nifty50_fund_api.json"


def main() -> None:
    captured: dict | None = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(response) -> None:
            nonlocal captured
            if response.url.endswith("/fs/v1/funds/57/details") and response.status == 200:
                captured = response.json()

        page.on("response", on_response)
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        browser.close()

    if not captured:
        raise SystemExit("Fund API not captured")
    OUT.write_text(json.dumps(captured, indent=2), encoding="utf-8")
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
