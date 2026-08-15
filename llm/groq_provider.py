"""Groq-backed LLMProvider implementation.

Construction never raises even without an API key — callers must check
`is_available` and handle the False case gracefully (this is the primary
degrade-gracefully boundary for LLM failures in the app).
"""
from __future__ import annotations

import logging

from llm.base import LLMProvider, LLMUnavailableError

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str | None, model: str, fallback_model: str):
        self._model = model
        self._fallback_model = fallback_model
        self._client = None

        if api_key:
            try:
                from groq import Groq

                self._client = Groq(api_key=api_key)
            except Exception:
                logger.exception("Failed to initialize Groq client")
                self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.4,
        max_tokens: int = 512,
    ) -> str:
        return self._complete(messages, temperature=temperature, max_tokens=max_tokens, json_mode=False)

    def chat_json(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        return self._complete(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)

    def _complete(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        if not self.is_available:
            raise LLMUnavailableError("Groq API key not configured")

        last_error: Exception | None = None
        for model in (self._model, self._fallback_model):
            try:
                kwargs = dict(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                completion = self._client.chat.completions.create(**kwargs)
                return completion.choices[0].message.content or ""
            except Exception as exc:  # groq.APIError, timeouts, rate limits, etc.
                logger.warning("Groq call failed on model %s: %s", model, exc)
                last_error = exc
                continue

        raise LLMUnavailableError(f"All Groq models failed: {last_error}") from last_error
