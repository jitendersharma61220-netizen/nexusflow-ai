"""Small reusable Streamlit UI pieces shared across pages."""
from __future__ import annotations

import streamlit as st

from agents.lead_extractor import LeadData
from scoring.lead_scoring import format_lead_badge

_FIELD_LABELS = {
    "name": "Name",
    "phone": "Phone",
    "budget": "Budget",
    "property_type": "Property Type",
    "configuration": "Configuration",
    "preferred_location": "Preferred Location",
    "purpose": "Purpose",
    "purchase_timeline": "Timeline",
    "requirements": "Requirements",
}


def render_lead_snapshot(lead: LeadData) -> None:
    st.subheader("📋 Lead Snapshot")
    st.markdown(f"**{format_lead_badge(lead.lead_status, lead.intent_score)}**")

    known = {
        _FIELD_LABELS[k]: v
        for k, v in lead.model_dump().items()
        if k in _FIELD_LABELS and v not in (None, "")
    }
    if not known:
        st.caption("No lead information captured yet — start chatting below.")
        return

    for label, value in known.items():
        st.markdown(f"**{label}:** {value}")

    if lead.ready_for_visit:
        st.success("✅ Site visit requested")


def render_demo_mode_badge(is_demo_mode: bool, backend_name: str) -> None:
    if is_demo_mode:
        st.sidebar.info(f"🧪 DEMO MODE — {backend_name}")
    else:
        st.sidebar.success(f"🟢 LIVE — {backend_name}")


def render_kb_upload(vector_store) -> None:
    """Sidebar panel letting the demo operator upload a real brochure/PDF so the AI's
    answers are grounded in it instead of (or alongside) the demo project data."""
    from rag.ingest import build_index, ingest_pdf

    with st.sidebar.expander("📎 Upload Project Knowledge (PDF)"):
        uploaded = st.file_uploader("Brochure / price list / FAQ", type=["pdf"], key="kb_upload")
        if uploaded is not None and st.button("Add to knowledge base", key="kb_upload_btn"):
            if vector_store is None:
                st.error("Knowledge base is unavailable right now.")
                return
            try:
                chunks = ingest_pdf(uploaded.read())
                if not chunks:
                    st.warning("Couldn't extract any text from that PDF.")
                    return
                build_index(chunks, source=uploaded.name, store=vector_store)
                st.success(f"Added {len(chunks)} chunks from {uploaded.name} to the knowledge base.")
            except Exception:
                st.error("Couldn't read that PDF — try another file.")
