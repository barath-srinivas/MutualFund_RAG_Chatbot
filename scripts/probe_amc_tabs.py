"""Probe AMC fund page tabs and API calls (Nifty Bank = 1839)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = (
    "https://www.icicipruamc.com/mutual-fund/index-funds/"
    "icici-prudential-nifty-bank-index-fund/1839"
)
OUT = Path(__file__).resolve().parent.parent / "corpus" / "raw" / "probe_tabs"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    api_hits: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        def on_response(response) -> None:
            url = response.url
            if "apimf.icicipruamc.com" not in url:
                return
            if "/fs/v1/" not in url and "/fls/" not in url:
                return
            try:
                body = response.text() if response.ok else ""
            except Exception:
                body = ""
            api_hits.append({"url": url, "status": response.status, "len": len(body)})
            if response.ok and body.startswith("{"):
                (OUT / f"api_{len(api_hits)}.json").write_text(body[:50000], encoding="utf-8")

        page.on("response", on_response)
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(3000)

        # Collect clickable labels
        labels = page.locator("button, a, [role='tab'], [role='button']").all_inner_texts()
        interesting = [
            t.strip()
            for t in labels
            if t and len(t.strip()) < 80
            and any(
                k in t.lower()
                for k in (
                    "fund manager",
                    "holding",
                    "portfolio",
                    "allocation",
                    "performance",
                    "risk",
                    "document",
                    "nav",
                )
            )
        ]
        print("Interesting controls:", sorted(set(interesting))[:40])

        # Try clicking by text
        tab_texts = [
            "Fund Manager",
            "Fund manager",
            "Top Holdings",
            "Holdings",
            "Portfolio",
            "Asset Allocation",
            "Fund Facts",
            "Riskometer",
        ]
        sections: dict[str, str] = {}
        for tab in tab_texts:
            try:
                loc = page.get_by_text(tab, exact=False).first
                if loc.is_visible(timeout=2000):
                    loc.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    sections[tab] = page.inner_text("main, [class*='fund'], #root")[:8000]
                    print(f"Clicked {tab!r}, section len={len(sections[tab])}")
            except Exception as e:
                print(f"Skip {tab!r}: {e}")

        (OUT / "body_initial.txt").write_text(page.inner_text("body"), encoding="utf-8")
        (OUT / "sections.json").write_text(
            json.dumps(sections, indent=2, ensure_ascii=False)[:200000],
            encoding="utf-8",
        )
        (OUT / "api_hits.json").write_text(
            json.dumps(api_hits, indent=2), encoding="utf-8"
        )
        browser.close()

    print("API URLs:")
    for h in api_hits:
        print(h["url"], h["status"], h["len"])


if __name__ == "__main__":
    main()
