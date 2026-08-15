"""WhatsApp-style chat simulator page."""
from __future__ import annotations

import streamlit as st

from agents.lead_extractor import LeadData
from agents.sales_agent import SalesAgent
from database import queries
from ui.components import render_lead_snapshot

_CHAT_CSS = """
<style>
.wa-header {
    background-color: #075E54;
    color: white;
    padding: 0.75rem 1rem;
    border-radius: 8px 8px 0 0;
    font-weight: 600;
}
.stChatMessage {
    max-width: 640px;
}
</style>
"""


def _init_session_state(project: dict) -> None:
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "lead" not in st.session_state:
        st.session_state["lead"] = LeadData()


def render_chat(agent: SalesAgent, project: dict) -> None:
    st.markdown(_CHAT_CSS, unsafe_allow_html=True)
    _init_session_state(project)

    with st.sidebar:
        render_lead_snapshot(st.session_state["lead"])

    st.markdown(
        f'<div class="wa-header">💬 {project.get("project_name", "Sales Chat")} — AI Assistant</div>',
        unsafe_allow_html=True,
    )

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_message = st.chat_input("Type a message (English / Hindi / Hinglish)...")
    if user_message is not None:
        st.session_state["messages"].append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        history = st.session_state["messages"][:-1]
        with st.chat_message("assistant"):
            with st.spinner("Typing..."):
                reply, updated_lead = agent.respond(
                    history, user_message, st.session_state["lead"]
                )
            st.markdown(reply)

        st.session_state["messages"].append({"role": "assistant", "content": reply})
        st.session_state["lead"] = updated_lead

        if "lead_id" not in st.session_state:
            st.session_state["lead_id"] = queries.create_lead(updated_lead)
        else:
            queries.update_lead(st.session_state["lead_id"], updated_lead)
        queries.log_message(st.session_state.get("lead_id"), "user", user_message)
        queries.log_message(st.session_state.get("lead_id"), "assistant", reply)

        st.rerun()
