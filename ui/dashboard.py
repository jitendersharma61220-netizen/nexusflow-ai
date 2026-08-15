"""Executive Lead Dashboard — KPIs, funnel, lead table, simulated sales alerts, analytics."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database import queries
from database.queries import get_db_status
from scoring.lead_scoring import format_lead_badge

_STATUS_OPTIONS = ["hot", "warm", "cold"]


def render_dashboard() -> None:
    st.title("📊 Executive Lead Dashboard")

    db_status = get_db_status()
    if db_status.warning:
        st.warning(db_status.warning)

    with st.expander("Filters", expanded=False):
        status_filter = st.multiselect(
            "Lead status", _STATUS_OPTIONS, default=_STATUS_OPTIONS,
            format_func=lambda s: s.upper(),
        )

    leads = queries.get_all_leads({"status": status_filter} if status_filter else None)
    stats = queries.get_dashboard_stats()

    if not leads:
        st.info("No leads yet — chat with the AI Sales Simulator to generate demo leads.")

    _render_kpis(stats)
    st.divider()
    _render_funnel(stats)
    st.divider()
    _render_hot_lead_alerts(leads)
    st.divider()
    _render_lead_table(leads)
    st.divider()
    _render_analytics(stats)


def _render_kpis(stats: dict) -> None:
    cols = st.columns(6)
    cols[0].metric("Total Leads", stats["total_leads"])
    cols[1].metric("Qualified Leads", stats["qualified_leads"])
    cols[2].metric("Hot Leads", stats["hot_leads"])
    cols[3].metric("Site Visits", stats["site_visits"])
    cols[4].metric("Conversion %", f"{stats['conversion_pct']}%")
    cols[5].metric("Avg Lead Score", stats["avg_score"])


def _render_funnel(stats: dict) -> None:
    st.subheader("Lead Funnel")
    total = stats["total_leads"]
    qualified = stats["qualified_leads"]
    warm_plus = stats["hot_leads"] + stats["warm_leads"]
    hot = stats["hot_leads"]
    visits = stats["site_visits"]

    fig = go.Figure(
        go.Funnel(
            y=["Total Enquiries", "Qualified", "Warm+", "Hot", "Site Visit"],
            x=[total, qualified, warm_plus, hot, visits],
            marker={"color": ["#93c5fd", "#60a5fa", "#fbbf24", "#f97316", "#ef4444"]},
        )
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)


def _render_hot_lead_alerts(leads: list[dict]) -> None:
    st.subheader("🚨 Sales Team Alerts")
    hot_leads = [l for l in leads if l.get("lead_status") == "hot"][:5]
    if not hot_leads:
        st.caption("No hot leads yet in this session.")
        return
    for lead in hot_leads:
        with st.container(border=True):
            st.markdown(f"**🚨 NEW HOT LEAD — {lead.get('name') or 'Unnamed'}**")
            st.markdown(
                f"Budget: {lead.get('budget') or '—'} | "
                f"Configuration: {lead.get('configuration') or '—'} | "
                f"Location: {lead.get('preferred_location') or '—'}"
            )
            st.markdown(
                f"{format_lead_badge(lead.get('lead_status', 'cold'), lead.get('intent_score', 0))} "
                f"{'| ✅ Site Visit Requested' if lead.get('ready_for_visit') else ''}"
            )
            st.caption("ACTION REQUIRED: Sales Executive Follow-up")


def _render_lead_table(leads: list[dict]) -> None:
    st.subheader("Leads")
    if not leads:
        st.caption("No leads to display.")
        return

    df = pd.DataFrame(leads)
    display_cols = {
        "name": "Name", "phone": "Phone", "budget": "Budget",
        "configuration": "Configuration", "intent_score": "Intent Score",
        "lead_status": "Status", "ready_for_visit": "Site Visit", "created_at": "Created At",
    }
    available = [c for c in display_cols if c in df.columns]
    df = df[available].rename(columns=display_cols)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_analytics(stats: dict) -> None:
    st.subheader("Analytics")
    cols = st.columns(3)
    cols[0].metric("Total Conversations", stats["total_conversations"])
    total = stats["total_leads"] or 1
    qualification_rate = round((stats["qualified_leads"] / total) * 100, 1)
    hot_pct = round((stats["hot_leads"] / total) * 100, 1)
    visit_pct = round((stats["site_visits"] / total) * 100, 1)
    cols[1].metric("Lead Qualification Rate", f"{qualification_rate}%")
    cols[2].metric("Hot Lead %", f"{hot_pct}%")
    st.caption(f"Site Visit %: {visit_pct}%")
