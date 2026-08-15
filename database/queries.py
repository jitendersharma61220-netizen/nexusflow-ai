"""Backend-agnostic data access layer. This is the only module the rest of the app
should import from `database/` — it decides Supabase vs local SQLite and guarantees
callers never see a raised exception from either backend."""
from __future__ import annotations

import logging
from functools import lru_cache

from config.settings import get_settings

logger = logging.getLogger(__name__)


class DBStatus:
    backend_name: str = "Local Storage"
    warning: str | None = None


_status = DBStatus()


def get_db_status() -> DBStatus:
    return _status


@lru_cache(maxsize=1)
def get_db():
    settings = get_settings()

    if not settings.demo_mode and settings.supabase_url and settings.supabase_key:
        try:
            from database.supabase_client import SupabaseBackend

            backend = SupabaseBackend(settings.supabase_url, settings.supabase_key)
            _status.backend_name = "Supabase"
            _status.warning = None
            return backend
        except Exception:
            logger.exception("Supabase init failed — falling back to local SQLite")
            _status.warning = "Supabase unavailable — using local storage for this session."

    from database.sqlite_client import SQLiteBackend

    _status.backend_name = "Local Storage"
    return SQLiteBackend()


def create_lead(lead, project_id: str | None = None, client_id: str | None = None,
                source: str = "whatsapp_demo") -> str | None:
    try:
        return get_db().create_lead(lead, project_id=project_id, client_id=client_id, source=source)
    except Exception:
        logger.exception("create_lead failed")
        _status.warning = "Storage temporarily unavailable — this session's data may not be saved."
        return None


def update_lead(lead_id: str | None, lead) -> None:
    if not lead_id:
        return
    try:
        get_db().update_lead(lead_id, lead)
    except Exception:
        logger.exception("update_lead failed")
        _status.warning = "Storage temporarily unavailable — this session's data may not be saved."


def log_message(lead_id: str | None, role: str, message: str) -> None:
    if not lead_id:
        return
    try:
        get_db().log_message(lead_id, role, message)
    except Exception:
        logger.exception("log_message failed")


def get_all_leads(filters: dict | None = None) -> list[dict]:
    try:
        return get_db().get_all_leads(filters)
    except Exception:
        logger.exception("get_all_leads failed")
        return []


def get_chat_history(lead_id: str) -> list[dict]:
    try:
        return get_db().get_chat_history(lead_id)
    except Exception:
        logger.exception("get_chat_history failed")
        return []


def get_dashboard_stats() -> dict:
    try:
        return get_db().get_dashboard_stats()
    except Exception:
        logger.exception("get_dashboard_stats failed")
        return {
            "total_leads": 0, "qualified_leads": 0, "hot_leads": 0, "warm_leads": 0,
            "cold_leads": 0, "site_visits": 0, "conversion_pct": 0.0, "avg_score": 0.0,
            "total_conversations": 0,
        }
