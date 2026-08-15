"""Local SQLite fallback backend — mirrors the Supabase schema so `queries.py` can be
completely backend-agnostic. Used automatically whenever Supabase isn't configured."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join("data", "local_store", "nexusflow.db")

_SCHEMA = """
create table if not exists leads (
    id text primary key,
    client_id text,
    project_id text,
    name text,
    phone text,
    email text,
    budget text,
    property_type text,
    configuration text,
    preferred_location text,
    purchase_timeline text,
    intent_score integer not null default 0,
    lead_status text not null default 'cold',
    ready_for_visit integer not null default 0,
    source text not null default 'whatsapp_demo',
    created_at text not null,
    updated_at text not null
);

create table if not exists chat_messages (
    id text primary key,
    lead_id text,
    role text not null,
    message text not null,
    timestamp text not null
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteBackend:
    def __init__(self, db_path: str = _DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def create_lead(self, lead, project_id: str | None = None, client_id: str | None = None,
                     source: str = "whatsapp_demo") -> str:
        lead_id = str(uuid.uuid4())
        now = _now()
        d = lead.model_dump()
        try:
            self._conn.execute(
                """insert into leads (id, client_id, project_id, name, phone, email, budget,
                   property_type, configuration, preferred_location, purchase_timeline,
                   intent_score, lead_status, ready_for_visit, source, created_at, updated_at)
                   values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (lead_id, client_id, project_id, d.get("name"), d.get("phone"), None,
                 d.get("budget"), d.get("property_type"), d.get("configuration"),
                 d.get("preferred_location"), d.get("purchase_timeline"), d.get("intent_score", 0),
                 d.get("lead_status", "cold"), int(d.get("ready_for_visit", False)), source, now, now),
            )
            self._conn.commit()
        except Exception:
            logger.exception("SQLite create_lead failed")
        return lead_id

    def update_lead(self, lead_id: str, lead) -> None:
        d = lead.model_dump()
        try:
            self._conn.execute(
                """update leads set name=?, phone=?, budget=?, property_type=?, configuration=?,
                   preferred_location=?, purchase_timeline=?, intent_score=?, lead_status=?,
                   ready_for_visit=?, updated_at=? where id=?""",
                (d.get("name"), d.get("phone"), d.get("budget"), d.get("property_type"),
                 d.get("configuration"), d.get("preferred_location"), d.get("purchase_timeline"),
                 d.get("intent_score", 0), d.get("lead_status", "cold"),
                 int(d.get("ready_for_visit", False)), _now(), lead_id),
            )
            self._conn.commit()
        except Exception:
            logger.exception("SQLite update_lead failed")

    def log_message(self, lead_id: str, role: str, message: str) -> None:
        try:
            self._conn.execute(
                "insert into chat_messages (id, lead_id, role, message, timestamp) values (?,?,?,?,?)",
                (str(uuid.uuid4()), lead_id, role, message, _now()),
            )
            self._conn.commit()
        except Exception:
            logger.exception("SQLite log_message failed")

    def get_all_leads(self, filters: dict | None = None) -> list[dict]:
        try:
            rows = self._conn.execute("select * from leads order by created_at desc").fetchall()
            leads = [dict(r) for r in rows]
        except Exception:
            logger.exception("SQLite get_all_leads failed")
            return []

        filters = filters or {}
        status_filter = filters.get("status")
        if status_filter:
            leads = [l for l in leads if l["lead_status"] in status_filter]
        return leads

    def get_chat_history(self, lead_id: str) -> list[dict]:
        try:
            rows = self._conn.execute(
                "select * from chat_messages where lead_id=? order by timestamp asc", (lead_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.exception("SQLite get_chat_history failed")
            return []

    def get_dashboard_stats(self) -> dict:
        try:
            leads = self.get_all_leads()
        except Exception:
            logger.exception("SQLite get_dashboard_stats failed")
            leads = []

        total = len(leads)
        hot = sum(1 for l in leads if l["lead_status"] == "hot")
        warm = sum(1 for l in leads if l["lead_status"] == "warm")
        cold = sum(1 for l in leads if l["lead_status"] == "cold")
        site_visits = sum(1 for l in leads if l["ready_for_visit"])
        qualified = hot + warm
        avg_score = round(sum(l["intent_score"] for l in leads) / total, 1) if total else 0.0
        conversion_pct = round((hot / total) * 100, 1) if total else 0.0

        try:
            total_conversations = self._conn.execute(
                "select count(distinct lead_id) as c from chat_messages"
            ).fetchone()["c"]
        except Exception:
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
