"""Central, cached application settings loaded from .env / environment / Streamlit secrets.

Never log or print an instance of Settings directly with its raw values — use
`repr(settings)` (masked) rather than dumping `__dict__`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str, default: str | None = None) -> str | None:
    """Read a config value from the environment, falling back to Streamlit secrets
    when running on Streamlit Community Cloud / Hugging Face Spaces with st.secrets."""
    value = os.getenv(key)
    if value is not None and value != "":
        return value
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


def _get_bool(key: str, default: bool) -> bool:
    raw = _get_env(key, str(default))
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_model: str
    groq_fallback_model: str
    supabase_url: str | None
    supabase_key: str | None
    demo_mode: bool

    def __repr__(self) -> str:
        def mask(v: str | None) -> str:
            if not v:
                return "None"
            return v[:4] + "…" if len(v) > 4 else "…"

        return (
            "Settings(groq_api_key="
            f"{mask(self.groq_api_key)}, groq_model={self.groq_model!r}, "
            f"groq_fallback_model={self.groq_fallback_model!r}, "
            f"supabase_url={'set' if self.supabase_url else 'None'}, "
            f"supabase_key={mask(self.supabase_key)}, demo_mode={self.demo_mode})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        groq_api_key=_get_env("GROQ_API_KEY"),
        groq_model=_get_env("GROQ_MODEL", "llama-3.3-70b-versatile"),
        groq_fallback_model=_get_env("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant"),
        supabase_url=_get_env("SUPABASE_URL"),
        supabase_key=_get_env("SUPABASE_KEY"),
        demo_mode=_get_bool("DEMO_MODE", True),
    )
