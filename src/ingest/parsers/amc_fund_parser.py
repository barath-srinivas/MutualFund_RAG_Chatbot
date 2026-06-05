"""Parse AMC SPA ingest bundle (rendered text + apimf fund details JSON)."""
from __future__ import annotations

import json
import re
from typing import Any

from src.ingest.amc_spa import resolve_direct_growth_scheme_code


def parse_amc_product_bundle(content: bytes) -> dict[str, Any]:
    """Decode JSON bundle produced by ``fetch_amc_product_page``."""
    warnings: list[str] = []
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "text": "",
            "pages": [],
            "tables": [],
            "sections": [],
            "warnings": [f"AMC bundle decode failed: {exc}"],
        }

    warnings.extend(str(w) for w in payload.get("warnings") or [])

    page_text = str(payload.get("page_text") or "")
    fund_api = payload.get("fund_api")
    page_url = str(payload.get("page_url") or "")
    tab_sections = payload.get("tab_sections") or {}
    extra_apis = payload.get("extra_apis") or {}
    scheme_code = payload.get("scheme_code") or resolve_direct_growth_scheme_code(fund_api)

    sections: list[dict[str, Any]] = []

    title = _title_from_api(fund_api) or _title_from_page(page_text) or "AMC scheme page"
    if page_url:
        sections.append(
            {
                "heading": title,
                "level": 1,
                "text": f"Official source: {page_url}",
                "tables": [],
            }
        )

    if scheme_code:
        sections.append(
            {
                "heading": "Scheme code (Direct Growth)",
                "level": 2,
                "text": f"schemeCode: {scheme_code}",
                "tables": [],
            }
        )

    holdings_text = _flatten_portfolio_holdings(extra_apis.get("portfolio_holdings"))
    if not holdings_text:
        holdings_tab = tab_sections.get("Holdings") if isinstance(tab_sections, dict) else None
        holdings_text = _flatten_holdings_tab(str(holdings_tab or ""))
    if not holdings_text:
        holdings_text = _flatten_holdings_tab(page_text)
    if holdings_text:
        sections.append(
            {
                "heading": "Top holdings",
                "level": 2,
                "text": holdings_text,
                "tables": _holdings_table(extra_apis.get("portfolio_holdings")),
            }
        )

    sectors_text = _flatten_portfolio_sectors(extra_apis.get("portfolio_sectors"))
    if sectors_text:
        sections.append(
            {
                "heading": "Sector allocation",
                "level": 2,
                "text": sectors_text,
                "tables": [],
            }
        )

    manager_text = _flatten_fund_managers(tab_sections, extra_apis)
    if manager_text:
        sections.append(
            {
                "heading": "Fund Manager",
                "level": 2,
                "text": manager_text,
                "tables": [],
            }
        )

    metrics_text = _flatten_metrics(extra_apis.get("metrics"))
    if metrics_text:
        sections.append(
            {
                "heading": "Fund metrics",
                "level": 2,
                "text": metrics_text,
                "tables": [],
            }
        )

    api_text = _flatten_fund_api(fund_api) if fund_api else ""
    if api_text:
        sections.append(
            {
                "heading": "Fund details (AMC API)",
                "level": 2,
                "text": api_text,
                "tables": _extract_tables_from_api(fund_api),
            }
        )

    for tab_name, tab_body in tab_sections.items():
        if tab_name in {"Holdings", "Fund Manager", "Sectors"}:
            continue
        cleaned = _clean_tab_section(tab_body)
        if cleaned:
            sections.append(
                {"heading": tab_name, "level": 2, "text": cleaned, "tables": []}
            )

    if page_text.strip():
        sections.append(
            {
                "heading": "Product page overview",
                "level": 2,
                "text": _clean_page_text(page_text),
                "tables": [],
            }
        )

    parts: list[str] = []
    for section in sections:
        heading = section.get("heading") or ""
        body = section.get("text") or ""
        if heading:
            parts.append(f"H{section.get('level', 2)}: {heading}")
        if body:
            parts.append(body)

    full_text = "\n\n".join(parts)
    tables = [t for section in sections for t in section.get("tables", [])]

    if not full_text.strip():
        warnings.append("No text extracted from AMC product bundle")

    return {
        "text": full_text,
        "pages": [full_text] if full_text else [],
        "tables": tables,
        "sections": sections,
        "warnings": warnings,
    }


def _flatten_holdings_tab(text: str) -> str:
    """Parse visible Holdings tab panel when apimf portfolio?type=HL was not captured."""
    rows = _holdings_rows_from_tab_text(text)
    if not rows:
        return ""
    lines = ["Top holdings by portfolio weight (%):"]
    for index, (name, weight) in enumerate(rows[:25], start=1):
        lines.append(f"{index}. {name}: {weight}%")
    return "\n".join(lines)


def _holdings_rows_from_tab_text(text: str) -> list[tuple[str, str]]:
    if not text.strip():
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    paired = _holdings_rows_percent_block_then_names(lines)
    if paired:
        return paired

    rows: list[tuple[str, str]] = []
    skip_prefixes = (
        "holdings",
        "top holdings",
        "company",
        "weight",
        "portfolio",
        "sector",
        "fund manager",
        "as on",
        "credit rating",
    )
    index = 0
    while index < len(lines):
        line = lines[index]
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in skip_prefixes):
            index += 1
            continue
        inline = re.match(r"^(.+?)\s+([\d.]+)\s*%$", line)
        if inline:
            rows.append((inline.group(1).strip(), inline.group(2).strip()))
            index += 1
            continue
        table = re.match(r"^(.+?)\s*\|\s*([\d.]+)\s*$", line)
        if table and table.group(1).strip().lower() != "company":
            rows.append((table.group(1).strip(), table.group(2).strip()))
            index += 1
            continue
        if index + 1 < len(lines):
            next_line = lines[index + 1]
            pct = re.match(r"^([\d.]+)\s*%$", next_line)
            if pct and not re.match(r"^[\d.]+\s*%$", line):
                rows.append((line, pct.group(1).strip()))
                index += 2
                continue
        index += 1
    return rows


def _holdings_rows_percent_block_then_names(lines: list[str]) -> list[tuple[str, str]]:
    """
    AMC product pages often render holdings as a column of weights, then names:
      Holdings / Credit Rating Profile / 18.92% / 14.05% / ... / HDFC Bank Ltd. / ...
    """
    start = 0
    for index, line in enumerate(lines):
        if line.strip().lower() == "holdings":
            start = index
            break

    window = lines[start : start + 80]
    percentages: list[str] = []
    names: list[str] = []
    for line in window:
        lower = line.lower()
        if lower in {"holdings", "sectors", "portfolio", "credit rating profile"}:
            continue
        if lower.startswith("view all") or lower.startswith("more details"):
            break
        pct = re.match(r"^([\d.]+)\s*%$", line)
        if pct:
            percentages.append(pct.group(1))
            continue
        if _looks_like_holding_name(line):
            names.append(line)
    if not percentages or not names:
        return []
    return list(zip(names, percentages))[:25]


def _looks_like_holding_name(line: str) -> bool:
    if len(line) < 4 or "%" in line:
        return False
    if line.lower().startswith(("view ", "more ", "fund ", "scheme ", "as on", "sip", "swp")):
        return False
    return bool(
        re.search(
            r"(Ltd\.?|Bank|Finance|India|NABARD|GOI|Corp\.?|Co\.?|Industries|Services)",
            line,
            re.IGNORECASE,
        )
    )


def _flatten_portfolio_holdings(api: Any) -> str:
    rows = _portfolio_rows(api)
    if not rows:
        return ""
    lines = ["Top holdings by portfolio weight (%):"]
    for index, row in enumerate(rows[:25], start=1):
        name = row.get("name", "")
        value = row.get("value", "")
        lines.append(f"{index}. {name}: {value}%")
    return "\n".join(lines)


def _flatten_portfolio_sectors(api: Any) -> str:
    rows = _portfolio_rows(api)
    if not rows:
        return ""
    lines = ["Sector allocation (%):"]
    for row in rows[:20]:
        lines.append(f"- {row.get('name', '')}: {row.get('value', '')}%")
    return "\n".join(lines)


def _portfolio_rows(api: Any) -> list[dict[str, Any]]:
    if not isinstance(api, dict):
        return []
    data = api.get("success", {}).get("data", api.get("data"))
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _holdings_table(api: Any) -> list[str]:
    rows = _portfolio_rows(api)
    if not rows:
        return []
    lines = ["Company | Weight %"]
    for row in rows[:25]:
        lines.append(f"{row.get('name', '')} | {row.get('value', '')}")
    return ["\n".join(lines)]


def _flatten_fund_managers(tab_sections: Any, extra_apis: dict[str, Any]) -> str:
    parts: list[str] = []
    if isinstance(tab_sections, dict):
        fm = tab_sections.get("Fund Manager") or tab_sections.get("Fund manager")
        if fm:
            parts.append(_extract_manager_names_from_text(str(fm)))

    managers = extra_apis.get("fund_managers")
    if isinstance(managers, list):
        for entry in managers:
            parts.append(json.dumps(entry, indent=2)[:2000])

    return "\n\n".join(p for p in parts if p.strip())


def _extract_manager_names_from_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Mr.") or line.startswith("Ms."):
            lines.append(line)
        elif line.lower().startswith("having experience"):
            if lines:
                lines[-1] = f"{lines[-1]} — {line}"
    if lines:
        return "Fund managers:\n" + "\n".join(f"- {name}" for name in lines)
    return ""


def _flatten_metrics(api: Any) -> str:
    if not isinstance(api, dict):
        return ""
    data = api.get("success", {}).get("data", api.get("data"))
    if not isinstance(data, dict):
        return ""
    lines: list[str] = []
    for key, block in data.items():
        if not isinstance(block, dict):
            continue
        title = block.get("title") or key
        desc = block.get("description") or block.get("value") or ""
        as_on = block.get("asOnDate") or ""
        line = f"{title}: {desc}"
        if as_on:
            line += f" (as on {as_on})"
        lines.append(line)
    return "\n".join(lines)


def _clean_tab_section(text: str) -> str:
    return _clean_page_text(text)[:6000]


def _title_from_api(fund_api: Any) -> str:
    if not isinstance(fund_api, dict):
        return ""
    data = fund_api.get("success", {}).get("data", fund_api.get("data", fund_api))
    if not isinstance(data, dict):
        return ""
    fund_name = data.get("fundName") or data.get("fund_name") or ""
    if fund_name:
        return f"ICICI Prudential {fund_name}".replace("ICICI Prudential ICICI", "ICICI")
    return ""


def _title_from_page(page_text: str) -> str:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if line == "INDEX FUNDS" and i + 1 < len(lines):
            return f"ICICI Prudential {lines[i + 1]}"
        if line.endswith("Fund") and "ICICI" not in line and i > 3:
            return f"ICICI Prudential {line}"
    return ""


def _clean_page_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    skip_prefixes = (
        "Funds",
        "Resources",
        "Services",
        "Shareholders",
        "INVESTOR",
        "SIGN IN",
        "MUTUAL FUND",
        "NEW TO MUTUAL FUNDS",
        "Consult our Experts",
        "Disclaimer:",
        "© 2026",
        "1800-",
    )
    cleaned: list[str] = []
    started = False
    for line in lines:
        if not line:
            continue
        if not started and any(line.startswith(p) for p in skip_prefixes):
            continue
        if line in {"INDEX FUNDS", "​", "HYBRID FUNDS", "EQUITY FUNDS"}:
            continue
        if line.startswith("Resources") or line.startswith("Tools"):
            break
        started = True
        cleaned.append(line)
    return "\n".join(cleaned)


def _flatten_fund_api(fund_api: Any) -> str:
    if not isinstance(fund_api, dict):
        return ""
    data = fund_api.get("success", {}).get("data", fund_api.get("data", fund_api))
    if not isinstance(data, dict):
        return json.dumps(fund_api, indent=2)

    lines: list[str] = []
    fund_name = data.get("fundName") or ""
    if fund_name:
        lines.append(f"Fund: {fund_name}")

    schemes = data.get("schemes") or []
    if isinstance(schemes, list):
        for scheme in schemes:
            if not isinstance(scheme, dict):
                continue
            lines.append(_format_scheme_block(scheme))

    return "\n\n".join(line for line in lines if line)


def _format_scheme_block(scheme: dict[str, Any]) -> str:
    fields = [
        ("Scheme", scheme.get("schemeName")),
        ("Scheme code", scheme.get("schemeCode")),
        ("Plan", scheme.get("schemeOption")),
        ("Category", scheme.get("subCategory")),
        ("Risk", scheme.get("risk")),
        ("Latest NAV", scheme.get("latestNav")),
        ("NAV date", scheme.get("navDate")),
        ("1Y return %", scheme.get("oneYear")),
        ("3Y return %", scheme.get("threeYear")),
        ("5Y return %", scheme.get("fiveYear")),
        ("Since inception %", scheme.get("sinceInception")),
        ("Min SIP", scheme.get("monthSIPAmt")),
        ("Min lumpsum", scheme.get("nipoAmt")),
        ("Investment goal", scheme.get("investGoal")),
        ("Expense ratio", scheme.get("expenseRatio")),
        ("TER", scheme.get("ter")),
    ]
    parts = [f"{label}: {value}" for label, value in fields if value not in (None, "")]
    return "\n".join(parts)


def _extract_tables_from_api(fund_api: Any) -> list[str]:
    if not isinstance(fund_api, dict):
        return []
    data = fund_api.get("success", {}).get("data", fund_api.get("data", fund_api))
    schemes = data.get("schemes") if isinstance(data, dict) else None
    if not isinstance(schemes, list) or not schemes:
        return []
    headers = ["Scheme", "Plan", "NAV", "1Y%", "3Y%", "5Y%", "Min SIP"]
    rows = [" | ".join(headers)]
    for scheme in schemes:
        if not isinstance(scheme, dict):
            continue
        rows.append(
            " | ".join(
                str(scheme.get(k, ""))
                for k in (
                    "schemeName",
                    "schemeOption",
                    "latestNav",
                    "oneYear",
                    "threeYear",
                    "fiveYear",
                    "monthSIPAmt",
                )
            )
        )
    return ["\n".join(rows)] if len(rows) > 1 else []
