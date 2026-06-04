"""Probe ICICI Pru AMC fund API for scheme id 57."""
from __future__ import annotations

import json
import re

import httpx

BASE = "https://www.icicipruamc.com"
FUND_ID = "57"


def main() -> None:
    js = httpx.get(f"{BASE}/static/js/main.624547e1.chunk.js", verify=False, timeout=60).text
    paths = sorted(set(re.findall(r'"/[a-zA-Z][a-zA-Z0-9_/-]{5,100}"', js)))
    fund_paths = [p.strip('"') for p in paths if "fund" in p.lower() or "/fs/" in p or "/cs/" in p]
    print("fund-related paths:", len(fund_paths))
    for p in fund_paths[:60]:
        print(" ", p)

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE}/mutual-fund/index-funds/icici-prudential-nifty-50-index-fund/57",
    }
    trials = [
        f"/fs/v1/funds/{FUND_ID}",
        f"/fs/v1/funds/details/{FUND_ID}",
        f"/fs/v1/funds/best-fund-details?fundId={FUND_ID}",
        f"/fs/v1/funds/best-fund-details/{FUND_ID}",
        f"/fs/v1/funds/schemes/options?fundId={FUND_ID}",
        f"/cs/v1/funds/{FUND_ID}",
        f"/cs/v1/funds?fundId={FUND_ID}",
        f"/fs/v1/funds?fundId={FUND_ID}",
        f"/fs/v1/funds?id={FUND_ID}",
    ]
    for path in trials:
        url = BASE + path
        try:
            r = httpx.get(url, headers=headers, verify=False, timeout=20)
            ct = r.headers.get("content-type", "")
            print(f"\n{path} -> {r.status_code} {ct} len={len(r.content)}")
            if "json" in ct and r.content:
                data = r.json()
                print(json.dumps(data, indent=2)[:1200])
        except Exception as e:
            print(path, e)


def probe_with_session() -> None:
    page_url = (
        f"{BASE}/mutual-fund/index-funds/icici-prudential-nifty-50-index-fund/{FUND_ID}"
    )
    api = f"{BASE}/fs/v1/funds/{FUND_ID}/details"
    with httpx.Client(verify=False, timeout=30, follow_redirects=True) as client:
        page = client.get(page_url)
        m = re.search(r'window\["_csrf_"\]\s*=\s*"([^"]+)"', page.text)
        token = m.group(1) if m else None
        print("csrf token:", (token[:48] + "...") if token else None)
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": page_url,
            "User-Agent": "Mozilla/5.0",
            "X-TS-AJAX-Request": "true",
        }
        if token:
            headers["X-TS-BP-Action"] = token
        for path in [f"/fs/v1/funds/{FUND_ID}/details", f"/fs/v1/funds/{FUND_ID}/performance"]:
            r = client.get(BASE + path, headers=headers)
            print(path, r.status_code, r.headers.get("content-type"), len(r.content))
            print(r.text[:600])


if __name__ == "__main__":
    probe_with_session()
