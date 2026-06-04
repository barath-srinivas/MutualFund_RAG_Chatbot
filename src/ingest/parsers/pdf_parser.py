from __future__ import annotations

import io
import re
from typing import Any

from pypdf import PdfReader


def parse_pdf(content: bytes) -> dict[str, Any]:
    """Extract text and table-like rows from PDF factsheets/KIM (task 1.7)."""
    warnings: list[str] = []
    pages: list[str] = []
    tables: list[str] = []

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        return {
            "text": "",
            "pages": [],
            "tables": [],
            "warnings": [f"PDF open failed: {exc}"],
        }

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            warnings.append("PDF is encrypted and could not be decrypted")

    for index, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            warnings.append(f"Page {index + 1} extract failed: {exc}")
            page_text = ""
        page_text = _normalize_whitespace(page_text)
        if page_text:
            pages.append(page_text)
            table_blocks = _extract_table_like_blocks(page_text)
            tables.extend(table_blocks)

    full_text = "\n\n".join(pages)
    if not full_text.strip():
        warnings.append("No text extracted from PDF (may be scanned image-only)")

    return {
        "text": full_text,
        "pages": pages,
        "tables": tables,
        "warnings": warnings,
    }


def _extract_table_like_blocks(page_text: str) -> list[str]:
    """Heuristic: preserve lines with fee/load/manager keywords as pseudo-tables."""
    keywords = (
        "expense ratio",
        "exit load",
        "fund manager",
        "managed by",
        "minimum",
        "sip",
        "benchmark",
        "riskometer",
    )
    blocks: list[str] = []
    lines = page_text.splitlines()
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            blocks.append("\n".join(buffer))
            buffer.clear()

    for line in lines:
        lower = line.lower()
        if any(keyword in lower for keyword in keywords) or re.search(r"\d+\.?\d*\s*%", line):
            buffer.append(line.strip())
        else:
            flush()
    flush()
    return blocks


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
