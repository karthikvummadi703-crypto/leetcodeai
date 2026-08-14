"""
Reusable OpenRouter HTTP client.

Handles streaming, retries, timeouts, and structured error handling.
All API key access is strictly from environment variables.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import orjson

from app.config import get_settings
from app.core import LLMError, get_logger

log = get_logger("openrouter")

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class _RetryableError(Exception):
    """Internal marker: transient failure worth retrying with backoff."""


class OpenRouterClient:
    """Async client for the OpenRouter chat completions API."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        settings = get_settings()
        self._api_key = settings.openrouter_api_key
        self._model = model or settings.openrouter_model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._top_p = top_p
        self._timeout = timeout
        self._max_retries = max_retries

        if not self._api_key:
            log.warning("OpenRouter API key is empty — LLM calls will fail")

    # ── Public accessors ───────────────────────────────────────

    @property
    def model(self) -> str:
        """The configured model identifier."""
        return self._model

    # ── Internal helpers ──────────────────────────────────────

    @staticmethod
    async def _backoff(attempt: int) -> None:
        """Exponential backoff with jitter before a retry."""
        delay = min(2 ** (attempt - 1), 8) + random.uniform(0, 0.5)
        await asyncio.sleep(delay)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": get_settings().backend_url,
            "X-Title": "LeetCode Guidance AI",
        }

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool = False,
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "top_p": self._top_p,
            "stream": stream,
        }

    # ── Non-streaming completion ──────────────────────────────

    async def complete(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """Send a chat completion request and return the full response text."""
        if not self._api_key:
            raise LLMError("OpenRouter API key is not configured.")

        payload = self._build_payload(messages, stream=False)
        url = f"{OPENROUTER_BASE_URL}/chat/completions"

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(url, headers=self._headers(), json=payload)

                elapsed = round(time.perf_counter() - start, 3)
                log.info(
                    "OpenRouter response: model={model} status={status} latency={elapsed}s attempt={attempt}",
                    model=self._model,
                    status=response.status_code,
                    elapsed=elapsed,
                    attempt=attempt,
                )

                if response.status_code == 429:
                    raise _RetryableError("OpenRouter rate limit exceeded.")
                if response.status_code >= 500:
                    raise _RetryableError(f"OpenRouter server error {response.status_code}.")
                if response.status_code >= 400:
                    raise LLMError(
                        f"OpenRouter rejected the request ({response.status_code}): "
                        f"{response.text[:200]}"
                    )

                data = orjson.loads(response.content)
                return data["choices"][0]["message"]["content"]

            except _RetryableError as exc:
                last_exc = exc
                log.warning("Attempt {attempt} retryable: {exc}", attempt=attempt, exc=exc)
            except LLMError:
                raise
            except httpx.TimeoutException:
                last_exc = LLMError("Request to OpenRouter timed out.")
                log.warning("Timeout on attempt {attempt}", attempt=attempt)
            except Exception as exc:  # noqa: BLE001 - any failure is retried before surfacing to the caller
                last_exc = exc
                log.warning("Attempt {attempt} failed: {exc}", attempt=attempt, exc=exc)

            await self._backoff(attempt)

        raise LLMError(
            f"OpenRouter request failed after {self._max_retries + 1} attempts: {last_exc}"
        )

    # ── Streaming completion ──────────────────────────────────

    async def stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """
        Yield incremental text chunks from a streaming completion.

        Temporary failures (connection errors, timeouts, 5xx, 429) are
        retried automatically. Once the first token has been produced the
        stream is committed — mid-stream failures propagate immediately so
        the user never receives duplicated or reordered output.
        """
        if not self._api_key:
            raise LLMError("OpenRouter API key is not configured.")

        payload = self._build_payload(messages, stream=True)
        url = f"{OPENROUTER_BASE_URL}/chat/completions"

        for attempt in range(1, self._max_retries + 2):
            start = time.perf_counter()
            started = False
            try:
                async for chunk in self._stream_once(url, payload):
                    if not started:
                        started = True
                        # First byte received — stop scheduling retries.
                    yield chunk

                elapsed = round(time.perf_counter() - start, 3)
                log.info(
                    "Stream completed in {elapsed}s (model={model}, attempt {attempt})",
                    elapsed=elapsed,
                    model=self._model,
                    attempt=attempt,
                )
                return
            except LLMError as exc:
                if started:
                    raise
                log.warning(
                    "Stream attempt {attempt} failed before first token: {exc}",
                    attempt=attempt,
                    exc=exc,
                )
                if attempt > self._max_retries:
                    raise LLMError(
                        f"Streaming request failed after {self._max_retries + 1} attempts: {exc}"
                    ) from exc
                await self._backoff(attempt)
            except httpx.TimeoutException:
                if started:
                    raise LLMError("Streaming request to OpenRouter timed out.") from None
                log.warning("Stream timeout on attempt {attempt}", attempt=attempt)
                if attempt > self._max_retries:
                    raise LLMError(
                        f"Streaming request timed out after {self._max_retries + 1} attempts."
                    ) from None
                await self._backoff(attempt)
            except Exception as exc:
                if started:
                    raise LLMError(f"Streaming failed: {exc}") from exc
                log.error("Stream attempt {attempt} failed: {exc}", attempt=attempt, exc=exc)
                if attempt > self._max_retries:
                    raise LLMError(f"Streaming failed: {exc}") from exc
                await self._backoff(attempt)

    async def _stream_once(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> AsyncIterator[str]:
        """Open one streaming connection and yield its text chunks."""
        async with (
            httpx.AsyncClient(timeout=self._timeout) as client,
            client.stream("POST", url, headers=self._headers(), json=payload) as response,
        ):
            if response.status_code != 200:
                body = await response.aread()
                log.error(
                    "Stream error {status}: {body}",
                    status=response.status_code,
                    body=body[:500],
                )
                raise LLMError(f"OpenRouter stream returned status {response.status_code}.")

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                chunk_str = line[6:].strip()
                if chunk_str == "[DONE]":
                    break
                try:
                    chunk = orjson.loads(chunk_str)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (orjson.JSONDecodeError, KeyError, IndexError):
                    continue
