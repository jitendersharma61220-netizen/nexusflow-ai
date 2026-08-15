"""Supabase Postgres backend — same interface as SQLiteBackend. Every method catches
its own exceptions and returns an empty/safe value rather than raising, so a runtime
Supabase outage degrades to "no data shown" instead of crashing the app."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SupabaseBackend:
    def __init__(self, url: str, key: str):
        from supabase import create_client

        self._client = create_client(url, key)

    def create_lead(self, lead, project_id: str | None = None, client_id: str | None = None,
                     source: str = "whatsapp_demo") -> str | None:
        d = lead.model_dump()
        payload = {
            "client_id": client_id,
            "project_id": project_id,
            "name": d.get("name"),
            "phone": d.get("phone"),
            "budget": d.get("budget"),
            "property_type": d.get("property_type"),
            "configuration": d.get("configuration"),
            "preferred_location": d.get("preferred_location"),
            "purchase_timeline": d.get("purchase_timeline"),
            "intent_score": d.get("intent_score", 0),
            "lead_status": d.get("lead_status", "cold"),
            "ready_for_visit": d.get("ready_for_visit", False),
            "source": source,
        }
        try:
            result = self._client.table("leads").insert(payload).execute()
            return result.data[0]["id"] if result.data else None
        except Exception:
            logger.exception("Supabase create_lead failed")
            return None

    def update_lead(self, lead_id: str, lead) -> None:
        d = lead.model_dump()
        payload = {
            "name": d.get("name"),
            "phone": d.get("phone"),
            "budget": d.get("budget"),
            "property_type": d.get("property_type"),
            "configuration": d.get("configuration"),
            "preferred_location": d.get("preferred_location"),
            "purchase_timeline": d.get("purchase_timeline"),
            "intent_score": d.get("intent_score", 0),
            "lead_status": d.get("lead_status", "cold"),
            "ready_for_visit": d.get("ready_for_visit", False),
        }
        try:
            self._client.table("leads").update(payload).eq("id", lead_id).execute()
        except Exception:
            logger.exception("Supabase update_lead failed")

    def log_message(self, lead_id: str, role: str, message: str) -> None:
        try:
            self._client.table("chat_messages").insert(
                {"lead_id": lead_id, "role": role, "message": message}
            ).execute()
        except Exception:
            logger.exception("Supabase log_message failed")

    def get_all_leads(self, filters: dict | None = None) -> list[dict]:
        try:
            query = self._client.table("leads").select("*").order("created_at", desc=True)
            filters = filters or {}
            status_filter = filters.get("status")
            if status_filter:
                query = query.in_("lead_status", status_filter)
            result = query.execute()
            return result.data or []
        except Exception:
            logger.exception("Supabase get_all_leads failed")
            return []

    def get_chat_history(self, lead_id: str) -> list[dict]:
        try:
            result = (
                self._client.table("chat_messages")
                .select("*")
                .eq("lead_id", lead_id)
                .order("timestamp")
                .execute()
            )
            return result.data or []
        except Exception:
            logger.exception("Supabase get_chat_history failed")
            return []

    def get_dashboard_stats(self) -> dict:
        leads = self.get_all_leads()
        total = len(leads)
        hot = sum(1 for l in leads if l.get("lead_status") == "hot")
        warm = sum(1 for l in leads if l.get("lead_status") == "warm")
        cold = sum(1 for l in leads if l.get("lead_status") == "cold")
        site_visits = sum(1 for l in leads if l.get("ready_for_visit"))
        qualified = hot + warm
        avg_score = round(sum(l.get("intent_score", 0) for l in leads) / total, 1) if total else 0.0
        conversion_pct = round((hot / total) * 100, 1) if total else 0.0

        try:
            msg_result = self._client.table("chat_messages").select("lead_id").execute()
            total_conversations = len({row["lead_id"] for row in (msg_result.data or [])})
        except Exception:
            logger.exception("Supabase conversation count failed")
            total_conversations = 0

        return {
            "total_leads": total,
            "qualified_leads": qualified,
            "hot_leads": hot,
            "warm_leads": warm,
            "cold_leads": cold,
            "site_visits": site_visits,
            "conversion_pct": conversion_pct,
            "avg_score": avg_score,
            "total_conversations": total_conversations,
        }
