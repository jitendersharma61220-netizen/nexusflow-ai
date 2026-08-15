"""Conversation orchestration hub: ties together the LLM reply, structured lead
extraction, and deterministic scoring for each turn."""
from __future__ import annotations

import logging
import re

from agents.lead_extractor import LeadData, LeadExtractor
from agents.prompts import (
    DEFLECTION_MESSAGE,
    OBJECTION_PLAYBOOK,
    RAG_ANSWER_INSTRUCTIONS,
    build_system_prompt,
)
from llm.base import LLMProvider, LLMUnavailableError
from rag.retriever import retrieve_context
from rag.vector_store import VectorStore
from scoring.lead_scoring import score_lead

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
FALLBACK_REPLY = (
    "I'm having trouble connecting right now — our sales team will follow up with you "
    "shortly. 🙏"
)
EMPTY_MESSAGE_REPLY = "Please type a message so I can help you 🙂"

_HIGH_STAKES_KEYWORDS = (
    "price", "cost", "kitna", "kimat", "available", "inventory", "unit", "sqft",
    "sq ft", "possession", "date", "rera", "brochure",
)

_OBJECTION_PATTERNS = {
    "price_too_high": (
        "mehnga", "mahenga", "bahut zyada", "too high", "too expensive", "expensive",
        "high price", "afford",
    ),
    "will_decide_later": (
        "baad mein", "later", "will decide", "think about it", "sochna hai", "sochenge",
    ),
    "send_details_whatsapp": (
        "whatsapp pe", "send details", "bhej do", "share details", "send on whatsapp",
    ),
    "wants_site_visit": (
        "site visit", "visit karni", "schedule a visit", "see the property", "dekhna hai",
    ),
}


def _detect_objection(text: str) -> str | None:
    lowered = text.lower()
    for key, keywords in _OBJECTION_PATTERNS.items():
        if any(kw in lowered for kw in keywords):
            return key
    return None


def _is_high_stakes_question(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in _HIGH_STAKES_KEYWORDS)


class SalesAgent:
    def __init__(self, llm: LLMProvider, project: dict, vector_store: VectorStore | None = None):
        self._llm = llm
        self._project = project
        self._extractor = LeadExtractor(llm)
        self._vector_store = vector_store

    @property
    def llm_available(self) -> bool:
        return self._llm.is_available

    def respond(
        self,
        history: list[dict],
        user_message: str,
        current_lead: LeadData | None = None,
    ) -> tuple[str, LeadData]:
        """Returns (assistant_reply, updated_lead)."""
        lead = current_lead or LeadData()

        cleaned = self._sanitize(user_message)
        if not cleaned:
            return EMPTY_MESSAGE_REPLY, lead

        reply = self._generate_reply(history, cleaned, lead)

        updated_lead = self._extractor.extract(
            history + [{"role": "user", "content": cleaned}],
            lead,
        )
        score, status = score_lead(updated_lead, self._project.get("location"))
        updated_lead = updated_lead.model_copy(update={"intent_score": score, "lead_status": status})

        return reply, updated_lead

    def _generate_reply(self, history: list[dict], user_message: str, lead: LeadData) -> str:
        context = None
        if self._vector_store is not None:
            context = retrieve_context(user_message, self._vector_store)

        if context is None and _is_high_stakes_question(user_message):
            # No grounded knowledge for a price/inventory/date-style question —
            # deflect directly rather than risking a hallucinated answer.
            return DEFLECTION_MESSAGE

        system_prompt = build_system_prompt(self._project, lead.model_dump())
        system_prompt += "\n" + RAG_ANSWER_INSTRUCTIONS.format(
            context=context or "NO MATCHING CONTEXT FOUND"
        )

        objection = _detect_objection(user_message)
        if objection:
            system_prompt += f"\nOBJECTION HANDLING GUIDANCE: {OBJECTION_PLAYBOOK[objection]}\n"

        messages = (
            [{"role": "system", "content": system_prompt}]
            + history[-20:]
            + [{"role": "user", "content": user_message}]
        )
        try:
            return self._llm.chat(messages)
        except LLMUnavailableError as exc:
            logger.warning("LLM unavailable during reply generation: %s", exc)
            return FALLBACK_REPLY

    @staticmethod
    def _sanitize(user_message: str) -> str:
        if not user_message:
            return ""
        cleaned = "".join(ch for ch in user_message if ch == "\n" or ch.isprintable())
        cleaned = cleaned.strip()
        return cleaned[:MAX_MESSAGE_LENGTH]
