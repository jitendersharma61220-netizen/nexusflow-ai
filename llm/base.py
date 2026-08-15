"""Provider-agnostic LLM interface so Groq can later be swapped for OpenAI/Gemini/Anthropic
without touching any calling code."""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMUnavailableError(Exception):
    """Raised when no LLM backend could produce a response after all retries/fallbacks."""


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.4,
        max_tokens: int = 512,
    ) -> str:
        """Return a free-text assistant reply for the given conversation."""

    @abstractmethod
    def chat_json(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> str:
        """Return a raw JSON string reply (caller is responsible for parsing/validating)."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is configured and able to serve requests."""
