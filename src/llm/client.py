from __future__ import annotations

import logging

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class LlmError(RuntimeError):
    pass


class GroqClient:
    """Groq chat client via OpenAI-compatible API (Phase 2.6)."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client

        settings = get_settings()
        if not settings.groq_api_key:
            raise LlmError("GROQ_API_KEY is not set in environment (.env).")

        try:
            from openai import OpenAI
        except Exception as exc:
            raise LlmError(
                "openai SDK is required for Groq (OpenAI-compatible). "
                "Install with: pip install -r requirements-phase2.txt"
            ) from exc

        self._client = OpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.llm_base_url,
        )
        return self._client

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        settings = get_settings()
        client = self._get_client()

        try:
            response = client.chat.completions.create(
                model=settings.llm_model,
                temperature=settings.llm_temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise LlmError(f"Groq request failed: {exc}") from exc

        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise LlmError("Groq returned empty content.")
        return content

