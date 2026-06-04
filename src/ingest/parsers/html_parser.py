from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Comment, Tag


# Tags commonly used for chrome on AMC / factsheet pages
_NOISE_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "nav",
    "footer",
    "header",
    "aside",
)
_NOISE_CLASS_PATTERNS = re.compile(
    r"(cookie|banner|footer|navbar|menu|sidebar|social|popup|modal|breadcrumb)",
    re.IGNORECASE,
)
_NOISE_ROLES = frozenset({"navigation", "banner", "contentinfo", "complementary"})


def parse_html(content: bytes, *, encoding: str | None = None) -> dict[str, Any]:
    """Extract main text from AMC scheme HTML pages (task 1.8)."""
    warnings: list[str] = []

    try:
        text_content = content.decode(encoding or "utf-8", errors="replace")
    except Exception as exc:
        return {
            "text": "",
            "pages": [],
            "tables": [],
            "sections": [],
            "warnings": [f"HTML decode failed: {exc}"],
        }

    soup = BeautifulSoup(text_content, "html.parser")
    _strip_noise(soup)

    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"content|scheme|fund", re.I))
        or soup.body
    )
    if main is None:
        warnings.append("No main content region found; used full document")
        main = soup

    title = ""
    if soup.title and soup.title.string:
        title = _clean_text(soup.title.string)

    sections = _extract_sections(main)
    if title and (not sections or sections[0]["heading"] != title):
        if sections and not sections[0]["heading"]:
            sections[0]["heading"] = title
        elif not sections:
            sections = [{"heading": title, "level": 1, "text": "", "tables": []}]

    tables = [table for section in sections for table in section.get("tables", [])]

    parts: list[str] = []
    for section in sections:
        heading = section.get("heading") or ""
        body = section.get("text") or ""
        if heading:
            level = section.get("level") or 2
            parts.append(f"H{level}: {heading}")
        if body:
            parts.append(body)

    full_text = "\n\n".join(p for p in parts if p)
    if not full_text.strip():
        full_text = _clean_text(main.get_text(separator="\n", strip=True))
        warnings.append("Fallback to full main text extraction")
        if full_text:
            sections = [{"heading": title or "Document", "level": 1, "text": full_text, "tables": tables}]

    return {
        "text": full_text,
        "pages": [full_text] if full_text else [],
        "tables": tables,
        "sections": sections,
        "warnings": warnings,
    }


def _strip_noise(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    for element in list(soup.find_all(True)):
        if not isinstance(element, Tag):
            continue
        attrs = element.attrs if isinstance(element.attrs, dict) else {}
        role = str(attrs.get("role") or "").lower()
        if role in _NOISE_ROLES:
            element.decompose()
            continue
        raw_class = attrs.get("class") or []
        classes = " ".join(raw_class) if isinstance(raw_class, list) else str(raw_class)
        element_id = str(attrs.get("id") or "")
        if _NOISE_CLASS_PATTERNS.search(classes) or _NOISE_CLASS_PATTERNS.search(element_id):
            element.decompose()


def _extract_sections(container: Tag) -> list[dict[str, Any]]:
    """Split HTML main content on h1–h3 boundaries for section-based chunking."""
    sections: list[dict[str, Any]] = []
    current_heading = ""
    current_level = 0
    current_parts: list[str] = []
    current_tables: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_level, current_parts, current_tables
        if not current_parts and not current_tables:
            return
        text = "\n\n".join(current_parts)
        sections.append(
            {
                "heading": current_heading,
                "level": current_level,
                "text": text,
                "tables": list(current_tables),
            }
        )
        current_parts = []
        current_tables = []

    for element in container.descendants:
        if not isinstance(element, Tag):
            continue
        if element.name in {"h1", "h2", "h3"}:
            flush()
            current_heading = _clean_text(element.get_text(separator=" ", strip=True))
            current_level = int(element.name[1])
            continue
        if element.name == "table" and element.find_parent("table") is None:
            table_text = _format_table(element)
            if table_text:
                current_tables.append(table_text)
                current_parts.append(table_text)
            continue
        if element.name == "p":
            text = _clean_text(element.get_text(separator=" ", strip=True))
            if len(text) > 2:
                current_parts.append(text)
            continue
        if element.name in {"ul", "ol"} and element.find_parent(["ul", "ol"]) is element:
            items = [
                _clean_text(li.get_text(separator=" ", strip=True))
                for li in element.find_all("li", recursive=False)
            ]
            items = [item for item in items if len(item) > 2]
            if items:
                current_parts.append("\n".join(f"- {item}" for item in items))

    flush()
    return sections


def _format_table(table: Tag) -> str:
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = [
            _clean_text(cell.get_text(separator=" ", strip=True))
            for cell in tr.find_all(["th", "td"])
        ]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()
