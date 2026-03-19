"""Thin LLM client wrapper with graceful degradation.

When ANTHROPIC_API_KEY is not set, all methods return None and the
system falls back to heuristic-only scoring.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds


@dataclass(frozen=True)
class LLMResponse:
    """Wrapper around a successful LLM call."""
    text: str
    model: str
    input_tokens: int
    output_tokens: int


def _get_api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or None


def _get_model() -> str:
    return os.environ.get("VIBE_LLM_MODEL", DEFAULT_MODEL)


class ClaudeClient:
    """Async Claude client with retry and graceful degradation.

    If ``ANTHROPIC_API_KEY`` is not set, ``available`` is False and all
    methods return ``None`` immediately.
    """

    def __init__(self) -> None:
        self._api_key = _get_api_key()
        self._model = _get_model()
        self._client: Any = None

    @property
    def available(self) -> bool:
        return self._api_key is not None

    def _ensure_client(self) -> Any:
        """Lazily construct the anthropic client."""
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore[import-untyped]
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            return self._client
        except ImportError:
            log.warning("anthropic SDK not installed — LLM features disabled")
            self._api_key = None
            return None

    async def evaluate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 2048,
    ) -> LLMResponse | None:
        """Send a free-form evaluation request.  Returns None on failure or no API key."""
        if not self.available:
            return None
        client = self._ensure_client()
        if client is None:
            return None

        backoff = INITIAL_BACKOFF
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                text = response.content[0].text if response.content else ""
                return LLMResponse(
                    text=text,
                    model=self._model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
            except Exception as exc:
                last_error = exc
                log.warning(
                    "LLM call attempt %d/%d failed: %s",
                    attempt, MAX_RETRIES, exc,
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(backoff)
                    backoff *= 2

        log.error("LLM call failed after %d retries: %s", MAX_RETRIES, last_error)
        return None

    async def structured_evaluate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 2048,
    ) -> dict[str, Any] | None:
        """Evaluate and parse the response as JSON.

        The system prompt should instruct the model to respond with valid JSON.
        Returns the parsed dict, or None if the call fails or JSON is malformed.
        """
        response = await self.evaluate(system_prompt, user_message, max_tokens=max_tokens)
        if response is None:
            return None
        return _parse_json_response(response.text)


def _parse_json_response(text: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response text, handling markdown fences."""
    cleaned = text.strip()
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        cleaned = "\n".join(lines[start:end]).strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        log.warning("LLM JSON response was not a dict: %s", type(result).__name__)
        return None
    except json.JSONDecodeError as exc:
        log.warning("Failed to parse LLM JSON response: %s", exc)
        return None


# Module-level singleton for convenience
_default_client: ClaudeClient | None = None


def get_client() -> ClaudeClient:
    """Return the module-level ClaudeClient singleton."""
    global _default_client
    if _default_client is None:
        _default_client = ClaudeClient()
    return _default_client
