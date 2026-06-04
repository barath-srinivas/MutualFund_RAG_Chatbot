"""Render ICICI AMC product page and capture API responses + visible text."""
from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright

URL = (
    "https://www.icicipruamc.com/mutual-fund/index-funds/"
    "icici-prudential-nifty-50-index-fund/57"
)


def main() -> None:
    api_hits: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(response) -> None:
            url = response.url
            if "apimf" in url or "/fs/v1/" in url:
                try:
                    body = response.text()[:2000] if response.ok else ""
                except Exception:
                    body = ""
                api_hits.append(
                    {
                        "url": url,
                        "status": response.status,
                        "content_type": response.headers.get("content-type", ""),
                        "body_preview": body,
                    }
                )

        page.on("response", on_response)
        page.goto(URL, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        browser.close()

    print("API hits:", len(api_hits))
    for hit in api_hits[:15]:
        print(json.dumps(hit, indent=2)[:800])
        print("---")
    from pathlib import Path

    out_dir = Path(__file__).resolve().parent.parent / "corpus" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "nifty50_rendered.txt").write_text(text, encoding="utf-8")
    (out_dir / "nifty50_api_hits.json").write_text(
        json.dumps(api_hits, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    fund_hits = [h for h in api_hits if "/fs/v1/funds" in h["url"] and "57" in h["url"]]
    print("BODY TEXT LEN:", len(text))
    print("fund detail API hits:", len(fund_hits))
    for hit in fund_hits:
        print(hit["url"], hit["status"], len(hit.get("body_preview", "")))


if __name__ == "__main__":
    main()
