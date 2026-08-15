"""Branded landing page shown before entering the chat simulator."""
from __future__ import annotations

import streamlit as st


def render_landing() -> None:
    st.markdown(
        """
        <div style="text-align:center; padding: 2rem 0 1rem 0;">
            <h1 style="margin-bottom:0;">NEXUSFLOW AI</h1>
            <p style="font-size:1.15rem; color:#6b7280; margin-top:0.25rem;">
                AI Sales Concierge for Real Estate
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    features = [
        "Lead Qualification",
        "Buyer Intent Detection",
        "Smart Conversations",
        "Automated Lead Scoring",
        "Site Visit Detection",
        "Sales Dashboard",
    ]

    cols = st.columns(3)
    for i, feature in enumerate(features):
        with cols[i % 3]:
            st.markdown(f"✓ {feature}")

    st.write("")
    _, center, _ = st.columns([1, 1, 1])
    with center:
        if st.button("🚀 Start Demo", use_container_width=True, type="primary"):
            st.session_state["page"] = "chat"
            st.rerun()
