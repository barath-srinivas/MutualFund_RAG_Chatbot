from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    scheme_id: str | None = None


class StructuredTablePayload(BaseModel):
    format: Literal["table"] = "table"
    title: str | None = None
    columns: list[str] = Field(..., min_length=2)
    rows: list[list[str]] = Field(..., min_length=1)
    summary: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citation_url: str | None = None
    last_updated: str
    type: Literal["answer", "refusal", "structured"] = "answer"
    refusal_reason: str | None = None
    structured: StructuredTablePayload | None = None
    scheme_id: str | None = None
