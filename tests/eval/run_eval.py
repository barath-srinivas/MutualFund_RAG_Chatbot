#!/usr/bin/env python3
"""
Phase 5 evaluation runner.

Scores golden factual and refusal suites against structural compliance gates
(citation allowlist, sentence cap, footer, route labels).

Usage:
  python tests/eval/run_eval.py --suite all --mock
  python tests/eval/run_eval.py --suite factual --live
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.eval.scoring import EvalCaseResult, score_factual_response, score_refusal_response

DEFAULT_FACTUAL = PROJECT_ROOT / "tests" / "eval" / "golden_factual.yaml"
DEFAULT_REFUSALS = PROJECT_ROOT / "tests" / "eval" / "golden_refusals.yaml"


def load_cases(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("cases") or [])


def build_mock_service():
    from datetime import datetime, timezone

    from src.api.chat import ChatService
    from src.retrieval.assembler import assemble_context
    from src.retrieval.models import RetrievedChunk, RetrievalResult
    from src.schemes.registry import get_scheme_registry

    class EvalRetriever:
        def retrieve(self, *, message: str, scheme_id: str | None):
            chunk = RetrievedChunk(
                chunk_id="eval-chunk",
                text=(
                    "Expense ratio (Direct Plan): 0.85%. Minimum SIP: Rs. 100. "
                    "Exit load: Nil. Benchmark: Nifty 50 TRI. Fund Manager: Example Manager since 2020."
                ),
                score=0.55,
                scheme_id=scheme_id,
                doc_type="amc_scheme",
                source_url="https://www.icicipruamc.com/mutual-fund/equity-funds/large-cap-fund",
                section="Fees",
                topic="fees",
                fetched_at=datetime(2026, 5, 31, tzinfo=timezone.utc),
            )
            result = RetrievalResult(chunks=[chunk], best_score=0.55, low_confidence=False)
            return result, assemble_context([chunk])

        def factsheet_fallback_url(self, scheme_id: str | None):
            return "https://www.icicipruamc.com/mutual-fund/equity-funds/large-cap-fund"

    class EvalLlm:
        def generate(self, *, system_prompt: str, user_prompt: str) -> str:
            return (
                "The direct plan expense ratio is 0.85% per the official AMC page. "
                "Minimum SIP is Rs. 100. "
                "Last updated from sources: 2026-05-31"
            )

    registry = get_scheme_registry()
    return ChatService(registry=registry, retriever=EvalRetriever(), llm=EvalLlm())


def build_live_service():
    from src.api.chat import ChatService
    from src.schemes.registry import get_scheme_registry

    return ChatService(registry=get_scheme_registry())


def run_suite(
    *,
    cases: list[dict],
    scorer,
    service,
    scheme_field: bool,
) -> tuple[list[EvalCaseResult], list[EvalCaseResult]]:
    passed: list[EvalCaseResult] = []
    failed: list[EvalCaseResult] = []

    for case in cases:
        explicit_scheme_id = case.get("scheme_id") if scheme_field else None
        response = service.chat(
            message=case["question"],
            explicit_scheme_id=explicit_scheme_id,
        )
        result = scorer(case, response)
        if result.passed:
            passed.append(result)
        else:
            failed.append(result)

    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run golden eval suites (Phase 5).")
    parser.add_argument(
        "--suite",
        choices=["factual", "refusals", "all"],
        default="all",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mocked retriever/LLM (CI-friendly, no Groq/Chroma required for factual structure).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use real retriever and Groq (requires index + GROQ_API_KEY).",
    )
    parser.add_argument("--factual-path", type=Path, default=DEFAULT_FACTUAL)
    parser.add_argument("--refusals-path", type=Path, default=DEFAULT_REFUSALS)
    parser.add_argument(
        "--min-factual-pass-rate",
        type=float,
        default=0.85,
        help="Release gate for factual suite (implementation.md §8.5).",
    )
    parser.add_argument(
        "--min-refusal-pass-rate",
        type=float,
        default=1.0,
        help="Release gate for refusal suite.",
    )
    args = parser.parse_args()

    if args.mock and args.live:
        print("Choose either --mock or --live, not both.", file=sys.stderr)
        return 2
    use_mock = args.mock or not args.live
    service = build_mock_service() if use_mock else build_live_service()

    exit_code = 0

    if args.suite in {"factual", "all"}:
        factual_cases = load_cases(args.factual_path)
        passed, failed = run_suite(
            cases=factual_cases,
            scorer=score_factual_response,
            service=service,
            scheme_field=True,
        )
        rate = len(passed) / len(factual_cases) if factual_cases else 0.0
        print(f"Factual: {len(passed)}/{len(factual_cases)} passed ({rate:.1%})")
        for item in failed[:10]:
            print(f"  FAIL {item.case_id}: {'; '.join(item.reasons)}")
        if rate < args.min_factual_pass_rate:
            print(f"Factual gate failed (< {args.min_factual_pass_rate:.0%}).", file=sys.stderr)
            exit_code = 1

    if args.suite in {"refusals", "all"}:
        refusal_cases = load_cases(args.refusals_path)
        passed, failed = run_suite(
            cases=refusal_cases,
            scorer=score_refusal_response,
            service=service,
            scheme_field=False,
        )
        rate = len(passed) / len(refusal_cases) if refusal_cases else 0.0
        print(f"Refusals: {len(passed)}/{len(refusal_cases)} passed ({rate:.1%})")
        for item in failed[:10]:
            print(f"  FAIL {item.case_id}: {'; '.join(item.reasons)}")
        if rate < args.min_refusal_pass_rate:
            print(f"Refusal gate failed (< {args.min_refusal_pass_rate:.0%}).", file=sys.stderr)
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
