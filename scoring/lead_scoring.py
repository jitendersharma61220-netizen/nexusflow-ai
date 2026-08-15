"""Deterministic, transparent HOT/WARM/COLD lead scoring — no ML, no LLM call.
Every point is explainable live to a client."""
from __future__ import annotations

import re

from agents.lead_extractor import LeadData

_PHONE_RE = re.compile(r"^\+?\d{10,13}$")

_SHORT_TIMELINE_KEYWORDS = (
    "immediate", "asap", "this week", "this month", "1 month", "2 month", "3 month",
    "1-3 month", "urgent", "ready to buy", "sunday", "monday", "tuesday", "wednesday",
    "thursday", "friday", "saturday", "tomorrow", "today",
)
_LONG_TIMELINE_KEYWORDS = ("later", "next year", "1 year", "not sure", "just browsing", "just looking")

_PRICE_INVENTORY_KEYWORDS = (
    "price", "cost", "budget", "available", "inventory", "unit", "sqft", "sq ft",
    "possession", "brochure", "payment plan", "emi",
)


def is_valid_phone(phone: str | None) -> bool:
    if not phone:
        return False
    cleaned = re.sub(r"[\s\-()]", "", phone)
    return bool(_PHONE_RE.match(cleaned))


def score_lead(lead: LeadData, project_location: str | None = None) -> tuple[int, str]:
    score = 0

    if lead.budget:
        score += 20

    if lead.configuration:
        score += 15

    timeline = (lead.purchase_timeline or "").lower()
    if any(kw in timeline for kw in _SHORT_TIMELINE_KEYWORDS):
        score += 15
    elif any(kw in timeline for kw in _LONG_TIMELINE_KEYWORDS):
        score += 0

    if is_valid_phone(lead.phone):
        score += 15

    requirements = (lead.requirements or "").lower()
    if any(kw in requirements for kw in _PRICE_INVENTORY_KEYWORDS):
        score += 15

    if lead.ready_for_visit:
        score += 10

    if project_location and lead.preferred_location:
        if project_location.lower() in lead.preferred_location.lower() or \
                lead.preferred_location.lower() in project_location.lower():
            score += 10

    score = max(0, min(100, score))

    if score >= 80:
        status = "hot"
    elif score >= 50:
        status = "warm"
    else:
        status = "cold"

    return score, status


def format_lead_badge(status: str, score: int) -> str:
    emoji = {"hot": "🔥 HOT LEAD", "warm": "🟡 WARM LEAD", "cold": "🔵 COLD LEAD"}
    return f"{emoji.get(status, '🔵 COLD LEAD')} — {score}"
