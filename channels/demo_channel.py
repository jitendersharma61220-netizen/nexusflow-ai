"""In-app WhatsApp simulator channel — backs the Streamlit chat UI directly via
st.session_state rather than any real messaging network."""
from __future__ import annotations

from channels.base import MessageChannel


class DemoChannel(MessageChannel):
    def __init__(self, session_state: dict):
        self._session_state = session_state
        self._session_state.setdefault("_demo_channel_inbox", [])

    def send(self, lead_id: str, text: str) -> None:
        self._session_state.setdefault("messages", []).append({"role": "assistant", "content": text})

    def receive(self) -> str | None:
        inbox = self._session_state.get("_demo_channel_inbox", [])
        if inbox:
            return inbox.pop(0)
        return None
