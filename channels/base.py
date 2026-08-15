"""Abstraction over how messages actually reach/leave a buyer, so the demo simulator can
later be swapped for a real WhatsApp Business API integration without touching the
conversation engine."""
from __future__ import annotations

from abc import ABC, abstractmethod


class MessageChannel(ABC):
    @abstractmethod
    def send(self, lead_id: str, text: str) -> None:
        """Deliver an outbound assistant message to the buyer."""

    @abstractmethod
    def receive(self) -> str | None:
        """Return the next inbound buyer message, if any."""
