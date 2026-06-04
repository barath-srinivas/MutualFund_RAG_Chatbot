from __future__ import annotations

import threading
import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    """Per-client fixed-window limiter for POST /chat (Phase 5.8)."""

    def __init__(self, *, requests_per_minute: int) -> None:
        self._rpm = max(1, requests_per_minute)
        self._window_seconds = 60.0
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, client_key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._hits[client_key] if now - t < self._window_seconds]
            if len(recent) >= self._rpm:
                self._hits[client_key] = recent
                return False
            recent.append(now)
            self._hits[client_key] = recent
            return True

    def retry_after_seconds(self, client_key: str) -> int:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._hits[client_key] if now - t < self._window_seconds]
            if not recent:
                return 1
            oldest = min(recent)
            wait = self._window_seconds - (now - oldest)
            return max(1, int(wait) + 1)


def client_key_from_request(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
