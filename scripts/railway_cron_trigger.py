#!/usr/bin/env python3
"""POST /internal/ingest on the API service (Railway private network)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 7200


def main() -> int:
    url = os.environ["INGEST_TRIGGER_URL"].strip()
    secret = os.environ["INGEST_TRIGGER_SECRET"].strip()
    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
            print(body)
            if response.status != 200:
                return 1
            payload = json.loads(body) if body.strip() else {}
            if payload.get("sources_failed", 0) > 0:
                print(f"Warning: ingest completed with {payload['sources_failed']} failed sources", file=sys.stderr)
            return 0
    except urllib.error.HTTPError as exc:
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
