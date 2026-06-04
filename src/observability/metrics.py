from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

ResponseKind = Literal["answer", "refusal", "structured"]


@dataclass
class ChatMetrics:
    """In-process counters and latency samples for /chat (Phase 5.2)."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=500), repr=False)

    total_requests: int = 0
    retrieval_hits: int = 0
    retrieval_misses: int = 0
    validator_failures: int = 0
    refusals_advisory: int = 0
    refusals_performance: int = 0
    refusals_out_of_scope: int = 0
    refusals_pii: int = 0
    refusals_other: int = 0
    answers: int = 0
    structured_responses: int = 0

    def record(
        self,
        *,
        response_type: ResponseKind,
        refusal_reason: str | None,
        retrieval_hit: bool | None,
        validator_failed: bool,
        latency_ms: float,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self._latencies_ms.append(latency_ms)

            if retrieval_hit is True:
                self.retrieval_hits += 1
            elif retrieval_hit is False:
                self.retrieval_misses += 1

            if validator_failed:
                self.validator_failures += 1

            if response_type == "answer":
                self.answers += 1
            elif response_type == "structured":
                self.structured_responses += 1
            elif response_type == "refusal":
                reason = (refusal_reason or "").lower()
                if reason == "advisory":
                    self.refusals_advisory += 1
                elif reason == "performance":
                    self.refusals_performance += 1
                elif reason == "out_of_scope":
                    self.refusals_out_of_scope += 1
                elif reason == "pii":
                    self.refusals_pii += 1
                else:
                    self.refusals_other += 1

        logger.info(
            "chat_metrics type=%s refusal_reason=%s retrieval_hit=%s validator_failed=%s latency_ms=%.1f",
            response_type,
            refusal_reason or "-",
            retrieval_hit if retrieval_hit is not None else "-",
            validator_failed,
            latency_ms,
        )

    def snapshot(self) -> dict[str, float | int]:
        with self._lock:
            total = self.total_requests
            refusals = (
                self.refusals_advisory
                + self.refusals_performance
                + self.refusals_out_of_scope
                + self.refusals_pii
                + self.refusals_other
            )
            retrieval_attempts = self.retrieval_hits + self.retrieval_misses
            latencies = sorted(self._latencies_ms)

            def rate(numerator: int, denominator: int) -> float:
                if denominator <= 0:
                    return 0.0
                return round(numerator / denominator, 4)

            return {
                "total_requests": total,
                "answers": self.answers,
                "structured_responses": self.structured_responses,
                "refusals_total": refusals,
                "refusals_advisory": self.refusals_advisory,
                "refusals_performance": self.refusals_performance,
                "refusals_out_of_scope": self.refusals_out_of_scope,
                "refusals_pii": self.refusals_pii,
                "refusals_other": self.refusals_other,
                "retrieval_hit_rate": rate(self.retrieval_hits, retrieval_attempts),
                "refusal_rate": rate(refusals, total),
                "validator_failure_rate": rate(self.validator_failures, total),
                "latency_p95_ms": _percentile(latencies, 95),
                "latency_p50_ms": _percentile(latencies, 50),
            }


_metrics = ChatMetrics()


def get_chat_metrics() -> ChatMetrics:
    return _metrics


def record_chat_outcome(
    *,
    response_type: ResponseKind,
    refusal_reason: str | None,
    retrieval_hit: bool | None,
    validator_failed: bool,
    latency_ms: float,
) -> None:
    _metrics.record(
        response_type=response_type,
        refusal_reason=refusal_reason,
        retrieval_hit=retrieval_hit,
        validator_failed=validator_failed,
        latency_ms=latency_ms,
    )


def _percentile(sorted_values: list[float], pct: int) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 1)
    rank = max(0, min(len(sorted_values) - 1, int(round((pct / 100.0) * (len(sorted_values) - 1)))))
    return round(sorted_values[rank], 1)
