"""NexusFlow AI — entrypoint Streamlit app."""
from __future__ import annotations

import json
import logging

import streamlit as st

from config.settings import get_settings
from database.queries import get_db, get_db_status
from llm.groq_provider import GroqProvider
from agents.sales_agent import SalesAgent
from rag.ingest import build_index, load_demo_project_as_documents
from rag.vector_store import VectorStore
from ui.landing import render_landing
from ui.chat import render_chat
from ui.dashboard import render_dashboard
from ui.components import render_demo_mode_badge, render_kb_upload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="NexusFlow AI — Sales Concierge",
    page_icon="🏙️",
    layout="centered",
)


@st.cache_data
def _load_demo_project() -> dict:
    with open("data/demo_project.json", "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def _build_vector_store(_project: dict) -> VectorStore | None:
    try:
        store = VectorStore()
        if not store.load():
            build_index(load_demo_project_as_documents(_project), source="demo_project", store=store)
        return store
    except Exception:
        logger.exception("RAG vector store unavailable — answers will not be grounded by retrieval")
        return None


@st.cache_resource
def _build_agent(_project: dict) -> SalesAgent:
    settings = get_settings()
    llm = GroqProvider(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        fallback_model=settings.groq_fallback_model,
    )
    vector_store = _build_vector_store(_project)
    return SalesAgent(llm, _project, vector_store)


def main() -> None:
    project = _load_demo_project()
    agent = _build_agent(project)

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    st.sidebar.title("NexusFlow AI")
    nav = st.sidebar.radio(
        "Navigate",
        ["Home", "Chat Simulator", "Dashboard"],
        index=["home", "chat", "dashboard"].index(st.session_state["page"])
        if st.session_state["page"] in ("home", "chat", "dashboard")
        else 0,
    )
    st.session_state["page"] = nav.lower().replace(" simulator", "").replace(" ", "_") \
        if nav != "Chat Simulator" else "chat"

    get_db()  # resolve the actual backend (Supabase vs local SQLite) once, up front
    db_status = get_db_status()
    render_demo_mode_badge(db_status.backend_name == "Local Storage", db_status.backend_name)
    if db_status.warning:
        st.sidebar.warning(f"⚠️ {db_status.warning}")

    if not agent.llm_available:
        st.sidebar.warning("⚠️ GROQ_API_KEY not set — chat will use graceful fallback replies.")

    render_kb_upload(_build_vector_store(project))

    if st.session_state["page"] == "home":
        render_landing()
    elif st.session_state["page"] == "chat":
        render_chat(agent, project)
    else:
        render_dashboard()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled application error")
        st.error("Something went wrong — please refresh. Our team has been notified.")
