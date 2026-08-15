from unittest.mock import MagicMock, patch

import pytest

from agents.lead_extractor import LeadData
from database.sqlite_client import SQLiteBackend


@pytest.fixture
def backend(tmp_path):
    return SQLiteBackend(db_path=str(tmp_path / "test.db"))


def test_create_and_fetch_lead(backend):
    lead = LeadData(name="Rahul", phone="9876543210", budget="1.5 Cr", intent_score=87, lead_status="hot")
    lead_id = backend.create_lead(lead)

    leads = backend.get_all_leads()
    assert len(leads) == 1
    assert leads[0]["name"] == "Rahul"
    assert leads[0]["intent_score"] == 87
    assert leads[0]["lead_status"] == "hot"
    assert lead_id == leads[0]["id"]


def test_update_lead(backend):
    lead = LeadData(name="Rahul")
    lead_id = backend.create_lead(lead)

    updated = LeadData(name="Rahul", budget="2 Cr", intent_score=60, lead_status="warm")
    backend.update_lead(lead_id, updated)

    leads = backend.get_all_leads()
    assert leads[0]["budget"] == "2 Cr"
    assert leads[0]["intent_score"] == 60


def test_log_and_fetch_chat_history(backend):
    lead_id = backend.create_lead(LeadData(name="Rahul"))
    backend.log_message(lead_id, "user", "Hi, 2 BHK available hai kya?")
    backend.log_message(lead_id, "assistant", "Yes! Let me help you.")

    history = backend.get_chat_history(lead_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_dashboard_stats_aggregate_correctly(backend):
    backend.create_lead(LeadData(name="Hot Lead", intent_score=90, lead_status="hot", ready_for_visit=True))
    backend.create_lead(LeadData(name="Warm Lead", intent_score=60, lead_status="warm"))
    backend.create_lead(LeadData(name="Cold Lead", intent_score=20, lead_status="cold"))

    stats = backend.get_dashboard_stats()
    assert stats["total_leads"] == 3
    assert stats["hot_leads"] == 1
    assert stats["warm_leads"] == 1
    assert stats["cold_leads"] == 1
    assert stats["site_visits"] == 1
    assert stats["qualified_leads"] == 2


def test_filters_by_status(backend):
    backend.create_lead(LeadData(name="Hot Lead", lead_status="hot"))
    backend.create_lead(LeadData(name="Cold Lead", lead_status="cold"))

    hot_only = backend.get_all_leads({"status": ["hot"]})
    assert len(hot_only) == 1
    assert hot_only[0]["name"] == "Hot Lead"


def test_empty_database_returns_zeroed_stats(backend):
    stats = backend.get_dashboard_stats()
    assert stats["total_leads"] == 0
    assert stats["conversion_pct"] == 0.0


def test_queries_degrade_gracefully_when_backend_raises():
    from database import queries

    broken_backend = MagicMock()
    broken_backend.get_all_leads.side_effect = Exception("connection refused")
    broken_backend.create_lead.side_effect = Exception("connection refused")

    with patch("database.queries.get_db", return_value=broken_backend):
        assert queries.get_all_leads() == []
        assert queries.create_lead(LeadData(name="X")) is None
