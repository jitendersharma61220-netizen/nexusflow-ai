"""Structured lead-field extraction from the conversation via Groq JSON mode, with
strict validation and graceful recovery from malformed LLM output."""
from __future__ import annotations

import json
import logging
from typing import Literal

from pydantic import BaseModel, ValidationError

from agents.prompts import EXTRACTION_PROMPT_TEMPLATE, JSON_RETRY_INSTRUCTION
from llm.base import LLMProvider, LLMUnavailableError

logger = logging.getLogger(__name__)


class LeadData(BaseModel):
    name: str | None = None
    phone: str | None = None
    budget: str | None = None
    property_type: str | None = None
    configuration: str | None = None
    preferred_location: str | None = None
    purpose: str | None = None
    purchase_timeline: str | None = None
    requirements: str | None = None
    intent_score: int = 0
    lead_status: Literal["hot", "warm", "cold"] = "cold"
    ready_for_visit: bool = False


class LeadExtractor:
    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def extract(self, conversation_history: list[dict], previous_lead: LeadData) -> LeadData:
        if not self._llm.is_available:
            return previous_lead

        extraction_prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            previous_lead_json=previous_lead.model_dump_json()
        )
        messages = (
            [{"role": "system", "content": extraction_prompt}]
            + conversation_history[-20:]
        )

        raw = self._try_extract(messages)
        if raw is not None:
            parsed = self._parse(raw)
            if parsed is not None:
                return self._merge(previous_lead, parsed)

        # One corrective retry.
        retry_messages = messages + [{"role": "system", "content": JSON_RETRY_INSTRUCTION}]
        raw = self._try_extract(retry_messages)
        if raw is not None:
            parsed = self._parse(raw)
            if parsed is not None:
                return self._merge(previous_lead, parsed)

        logger.warning("Lead extraction failed twice; keeping previous lead state")
        return previous_lead

    def _try_extract(self, messages: list[dict]) -> str | None:
        try:
            return self._llm.chat_json(messages)
        except LLMUnavailableError as exc:
            logger.warning("LLM unavailable during lead extraction: %s", exc)
            return None

    def _parse(self, raw: str) -> LeadData | None:
        try:
            data = json.loads(raw)
            return LeadData.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Invalid extraction JSON: %s", exc)
            return None

    def _merge(self, previous: LeadData, new: LeadData) -> LeadData:
        """Never let a newly-extracted null overwrite a previously known value."""
        merged = previous.model_dump()
        for key, value in new.model_dump().items():
            if key in ("intent_score", "lead_status"):
                continue  # computed separately by the deterministic scorer
            if value not in (None, ""):
                merged[key] = value
            elif key == "ready_for_visit" and value is True:
                merged[key] = True
        merged["ready_for_visit"] = previous.ready_for_visit or new.ready_for_visit
        return LeadData.model_validate(merged)
