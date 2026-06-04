from __future__ import annotations

import logging
import time
from datetime import date

from src.guardrails.classifier import classify_query
from src.guardrails.pii import detect_pii
from src.guardrails.structured_request import is_catalog_query
from src.guardrails.structured_response import (
    parse_structured_json,
    structured_to_chat_dict,
    validate_structured_response,
)
from src.guardrails.templates import advisory_refusal, out_of_scope_refusal, performance_template, pii_refusal
from src.guardrails.validator import validate_answer
from src.llm.client import GroqClient, LlmError
from src.llm.prompts import (
    build_system_prompt,
    build_user_prompt,
    fallback_answer,
    holdings_unavailable_answer,
)
from src.retrieval.intent import QueryIntent, detect_intent
from src.retrieval.scheme_scope import answer_mentions_foreign_fund
from src.retrieval.catalog import build_catalog_context
from src.retrieval.preprocessor import normalize_query, resolve_scheme_id
from src.ingest.manifest import load_manifest
from src.retrieval.citations import preferred_citation_url
from src.retrieval.assembler import assemble_context
from src.retrieval.fund_manager_answer import build_fund_manager_answer
from src.retrieval.models import AssembledContext
from src.retrieval.retriever import Retriever
from src.observability.metrics import record_chat_outcome
from src.schemes.registry import SchemeRegistry

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(
        self,
        *,
        registry: SchemeRegistry,
        retriever: Retriever | None = None,
        llm: GroqClient | None = None,
    ) -> None:
        self._registry = registry
        self._retriever = retriever or Retriever()
        self._llm = llm or GroqClient()

    def chat(self, *, message: str, explicit_scheme_id: str | None) -> dict:
        started = time.perf_counter()
        retrieval_hit: bool | None = None
        validator_failed = False

        def finish(result: dict) -> dict:
            from src.config.settings import get_settings

            if get_settings().metrics_enabled:
                record_chat_outcome(
                    response_type=result.get("type", "answer"),
                    refusal_reason=result.get("refusal_reason"),
                    retrieval_hit=retrieval_hit,
                    validator_failed=validator_failed,
                    latency_ms=(time.perf_counter() - started) * 1000.0,
                )
            return result

        normalized = normalize_query(message)
        today = date.today()
        if detect_pii(normalized):
            return finish(pii_refusal(today=today))

        scheme_id = resolve_scheme_id(
            normalized,
            explicit_scheme_id=explicit_scheme_id,
            registry=self._registry,
        )
        route = classify_query(
            message=normalized,
            registry=self._registry,
            explicit_scheme_id=explicit_scheme_id,
            resolved_scheme_id=scheme_id,
        )

        if route.label == "advisory":
            return finish(advisory_refusal(today=today))
        if route.label == "out_of_scope":
            return finish(out_of_scope_refusal(today=today, registry=self._registry))
        if route.label == "performance":
            factsheet_url = self._retriever.factsheet_fallback_url(route.scheme_id)
            return finish(performance_template(today=today, factsheet_url=factsheet_url))

        is_structured = route.label == "structured"
        if is_structured and is_catalog_query(normalized):
            context = build_catalog_context(
                message=normalized,
                registry=self._registry,
                retriever=self._retriever,
            )
            retrieval_hit = context is not None and bool(context.context_text.strip())
        elif is_structured:
            retrieval_result, context = self._retriever.retrieve(
                message=normalized, scheme_id=route.scheme_id
            )
            retrieval_hit = _retrieval_hit(retrieval_result, context)
        else:
            retrieval_result, context = self._retriever.retrieve(
                message=normalized, scheme_id=route.scheme_id
            )
            retrieval_hit = _retrieval_hit(retrieval_result, context)

        intent = detect_intent(normalized)
        scheme = self._registry.get(route.scheme_id) if route.scheme_id else None
        scheme_name = scheme.display_name if scheme else None

        if context is None or not context.context_text.strip():
            factsheet_url = self._retriever.factsheet_fallback_url(route.scheme_id)
            if intent == QueryIntent.HOLDINGS and scheme_name:
                answer, citation_url, last_updated = holdings_unavailable_answer(
                    scheme_display_name=scheme_name,
                    factsheet_url=factsheet_url,
                    today=today,
                )
            else:
                answer, citation_url, last_updated = fallback_answer(
                    scheme_id=route.scheme_id,
                    factsheet_url=factsheet_url,
                    today=today,
                )
            return finish({
                "answer": answer,
                "citation_url": citation_url,
                "last_updated": last_updated.isoformat(),
                "type": "answer",
                "refusal_reason": None,
                "structured": None,
            })

        system_prompt = build_system_prompt(
            structured=is_structured,
            fund_management=intent == QueryIntent.FUND_MANAGEMENT,
        )
        context_text = _generation_context_text(context, intent=intent)
        user_prompt = build_user_prompt(
            question=normalized,
            context=context_text,
            structured=is_structured,
            scheme_display_name=scheme_name,
        )

        last_updated = context.last_updated or date.today()
        from src.config.settings import get_settings

        settings = get_settings()
        preferred_url = preferred_citation_url(
            scheme_id=route.scheme_id,
            candidate_urls=context.citation_urls,
            manifest=load_manifest(),
            allowed_domains=settings.allowed_domain_list(),
        )

        if (
            intent == QueryIntent.FUND_MANAGEMENT
            and scheme_name
            and preferred_url
            and context is not None
        ):
            direct = build_fund_manager_answer(
                scheme_display_name=scheme_name,
                context=context,
                citation_url=preferred_url,
                last_updated=last_updated,
            )
            if direct:
                validated = validate_answer(
                    direct,
                    citation_url=preferred_url,
                    last_updated=last_updated,
                    allow_performance_numbers=False,
                    max_sentences=settings.answer_max_sentences_fund_management,
                )
                if validated.citation_url:
                    return finish({
                        "answer": validated.answer,
                        "citation_url": validated.citation_url,
                        "last_updated": validated.last_updated.isoformat()
                        if validated.last_updated
                        else last_updated.isoformat(),
                        "type": "answer",
                        "refusal_reason": None,
                        "structured": None,
                    })

        errors: list[str] = []

        for attempt in range(1, settings.llm_max_retries + 2):
            try:
                draft = self._llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
            except LlmError as exc:
                errors.append(str(exc))
                break

            if is_structured:
                try:
                    payload = parse_structured_json(draft)
                    validated = validate_structured_response(
                        payload,
                        registry=self._registry,
                        citation_url=preferred_url,
                        last_updated=last_updated,
                    )
                    return finish(structured_to_chat_dict(validated))
                except (ValueError, TypeError) as exc:
                    errors.append(f"structured parse: {exc}")
                    validator_failed = True
                    continue

            max_sentences = (
                settings.answer_max_sentences_fund_management
                if intent == QueryIntent.FUND_MANAGEMENT
                else settings.answer_max_sentences
            )
            validated = validate_answer(
                draft,
                citation_url=preferred_url,
                last_updated=last_updated,
                allow_performance_numbers=False,
                max_sentences=max_sentences,
            )
            if (
                route.scheme_id
                and answer_mentions_foreign_fund(
                    validated.answer,
                    target_scheme_id=route.scheme_id,
                    registry=self._registry,
                )
            ):
                errors.append("Answer referenced a different fund than requested.")
                validator_failed = True
                continue

            if validated.citation_url:
                return finish({
                    "answer": validated.answer,
                    "citation_url": validated.citation_url,
                    "last_updated": validated.last_updated.isoformat()
                    if validated.last_updated
                    else last_updated.isoformat(),
                    "type": "answer",
                    "refusal_reason": None,
                    "structured": None,
                })
            errors.append("Validator rejected citation URL.")
            validator_failed = True

        logger.warning("Chat generation failed; falling back. errors=%s", errors[:2])
        factsheet_url = self._retriever.factsheet_fallback_url(route.scheme_id)
        answer, citation_url, last_updated = fallback_answer(
            scheme_id=route.scheme_id,
            factsheet_url=factsheet_url,
            today=today,
        )
        return finish({
            "answer": answer,
            "citation_url": citation_url,
            "last_updated": last_updated.isoformat(),
            "type": "answer",
            "refusal_reason": None,
            "structured": None,
        })


def _retrieval_hit(retrieval_result, context: AssembledContext | None) -> bool:
    if context is None or not context.context_text.strip():
        return False
    return not retrieval_result.low_confidence


def _generation_context_text(context: AssembledContext, *, intent: QueryIntent) -> str:
    """For fund-manager questions, pass only Fund Manager chunks so the LLM does not add TER/SIP."""
    if intent != QueryIntent.FUND_MANAGEMENT:
        return context.context_text
    fm_chunks = [
        c
        for c in context.chunks
        if (c.section or "").strip().lower() == "fund manager"
    ]
    if not fm_chunks:
        return context.context_text
    return assemble_context(fm_chunks).context_text
