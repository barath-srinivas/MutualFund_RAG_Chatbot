from __future__ import annotations

import json
from datetime import date


def build_system_prompt(*, structured: bool = False, fund_management: bool = False) -> str:
    if structured:
        return build_structured_system_prompt()
    if fund_management:
        sentence_rule = (
            "- Maximum 2 sentences: (1) list every fund manager name from the context "
            "(comma-separated); (2) optional short pointer to the official source — do not paste the URL in prose.\n"
            "- Do NOT include expense ratio, TER, exit load, minimum SIP, NAV, AUM, or holdings unless the user "
            "explicitly asked for those facts.\n"
        )
        scope_rule = (
            "For fund manager / who manages questions: answer with manager names only (and tenure if stated). "
            "Ignore other facts in the context blocks.\n"
        )
    else:
        sentence_rule = "- Maximum 3 sentences.\n"
        scope_rule = (
            "If specific figures (expense ratio, exit load, minimum SIP, manager name, benchmark) appear in the "
            "context, state them clearly. "
        )
    return (
        "You are a facts-only mutual fund FAQ assistant. "
        "Answer only using the provided context. "
        "Answer only for the Target scheme named in the user message. "
        "Never substitute a different fund (e.g. do not answer about NASDAQ 100 when asked about PHD Fund). "
        "Do not answer about random ETFs or funds that are not ICICI Prudential schemes in scope. "
        "If the context does not list portfolio companies or holdings for the Target scheme, say so clearly "
        "and do not invent holdings from another fund's factsheet. "
        f"{scope_rule}"
        "Only say information is unavailable when it is truly absent from the context.\n\n"
        "Hard rules:\n"
        f"{sentence_rule}"
        "- State facts directly. Do not mention 'context', 'provided context', retrieval, or whether "
        "information is or is not in the sources — only the factual answer.\n"
        "- Do not paste URLs in the answer; the API attaches the official source link separately.\n"
        "- No investment advice, recommendations, comparisons, or return calculations.\n"
        "- For fund management questions, state only names/dates/roles explicitly present in the context.\n"
        "- Do not cite Groww.\n"
        "- End with a footer: 'Last updated from sources: YYYY-MM-DD'.\n"
    )


def build_structured_system_prompt() -> str:
    example = {
        "summary": "Direct-plan expense ratios for in-scope ICICI Prudential schemes from official sources.",
        "table": {
            "title": "Expense ratio by scheme",
            "columns": ["Scheme", "Direct plan TER"],
            "rows": [
                ["ICICI Prudential Multi Asset Fund", "0.53% p.a."],
                ["ICICI Prudential Large Cap Fund", "0.85% p.a."],
            ],
        },
    }
    return (
        "You are a facts-only mutual fund FAQ assistant. "
        "The user asked for a TABLE. Reply with JSON only (no markdown outside JSON).\n\n"
        "Scope: exactly 10 ICICI Prudential direct-growth schemes in the context blocks. "
        "Ignore ETFs, FOFs, or other funds not labelled with scheme_id in the context.\n\n"
        "Output schema:\n"
        f"{json.dumps(example, indent=2)}\n\n"
        "Rules:\n"
        "- Include one row per in-scope scheme where the requested fact appears in context; omit schemes with no data.\n"
        "- First column: scheme display name. Other columns: the requested fact (e.g. TER, exit load, fund manager).\n"
        "- summary: at most 2 short sentences; do not include URLs in JSON (citation is added separately).\n"
        "- No investment advice, comparisons, or performance return calculations.\n"
        "- Use only facts explicitly present in the context.\n"
    )


def build_user_prompt(
    *,
    question: str,
    context: str,
    structured: bool = False,
    scheme_display_name: str | None = None,
) -> str:
    if structured:
        return build_structured_user_prompt(
            question=question, context=context, scheme_display_name=scheme_display_name
        )
    target = ""
    if scheme_display_name:
        target = f"Target scheme: {scheme_display_name}\n\n"
    return (
        f"{target}"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Context (use this only):\n"
        f"{context.strip()}\n"
    )


def build_structured_user_prompt(
    *,
    question: str,
    context: str,
    scheme_display_name: str | None = None,
) -> str:
    target = ""
    if scheme_display_name:
        target = f"Target scheme: {scheme_display_name}\n\n"
    return (
        f"{target}"
        "Question:\n"
        f"{question.strip()}\n\n"
        "Context (use this only — each block is one in-scope scheme):\n"
        f"{context.strip()}\n\n"
        "Return JSON matching the schema from the system message.\n"
    )


def holdings_unavailable_answer(
    *, scheme_display_name: str, factsheet_url: str | None, today: date
) -> tuple[str, str | None, date]:
    if factsheet_url:
        answer = (
            f"I do not have a verified portfolio holdings list for {scheme_display_name} "
            "in the indexed sources. "
            "Please use the official source link for the latest company names and weights. "
            f"Last updated from sources: {today.isoformat()}"
        )
        return answer, factsheet_url, today
    answer = (
        f"I do not have a verified portfolio holdings list for {scheme_display_name} "
        "in the indexed sources. "
        f"Last updated from sources: {today.isoformat()}"
    )
    return answer, None, today


def fallback_answer(*, scheme_id: str | None, factsheet_url: str | None, today: date) -> tuple[str, str | None, date]:
    if factsheet_url:
        answer = (
            "I do not have verified information for this question in the available sources. "
            "Please use the official source link below for this scheme. "
            f"Last updated from sources: {today.isoformat()}"
        )
        return answer, factsheet_url, today
    answer = (
        "I do not have verified information for this question in the available sources. "
        f"Last updated from sources: {today.isoformat()}"
    )
    return answer, None, today
