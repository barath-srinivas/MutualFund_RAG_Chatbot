"""Probe AMC mutual fund product page HTML for extractable content."""
import json
import re
import sys

import httpx

URL = sys.argv[1] if len(sys.argv) > 1 else (
    "https://www.icicipruamc.com/mutual-fund/index-funds/icici-prudential-nifty-50-index-fund/57"
)

r = httpx.get(URL, verify=False, timeout=60, follow_redirects=True)
html = r.text
print("status", r.status_code, "bytes", len(r.content))

m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
if m:
    data = json.loads(m.group(1))
    print("__NEXT_DATA__ keys", data.keys())
    print(json.dumps(data, indent=2)[:3000])
else:
    print("no __NEXT_DATA__")
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    for i, s in enumerate(sorted(scripts, key=len, reverse=True)[:3]):
        print(f"script {i} len={len(s)} preview={s[:200]!r}")

# Search main JS for API paths
import re as _re

js_url = "https://www.icicipruamc.com/static/js/main.624547e1.chunk.js"
js = httpx.get(js_url, verify=False, timeout=60).text
paths = sorted(set(_re.findall(r'"/[a-zA-Z][a-zA-Z0-9_/-]{8,80}"', js)))
print("sample paths from main.js:", [p for p in paths if "api" in p.lower() or "fund" in p.lower()][:25])

# API probe common patterns
candidates = [
    "https://www.icicipruamc.com/api/mutual-fund/57",
    "https://www.icicipruamc.com/api/v1/mutual-fund/57",
    "https://www.icicipruamc.com/mfapi/v1/getFundDetails/57",
    "https://www.icicipruamc.com/mfapi/getFundDetails/57",
    "https://www.icicipruamc.com/api/fund-details/57",
    "https://www.icicipruamc.com/api/mutualfund/57",
    "https://www.icicipruamc.com/api/MutualFund/57",
]
for api in candidates:
    try:
        ar = httpx.get(api, verify=False, timeout=15, headers={"Accept": "application/json"})
        print(api, ar.status_code, ar.headers.get("content-type"), len(ar.content))
        if "json" in (ar.headers.get("content-type") or ""):
            print(ar.text[:400])
    except Exception as e:
        print(api, e)
