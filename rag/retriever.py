"""The anti-hallucination gate: returns None when nothing in the knowledge base is a
confident match, which the sales agent uses to trigger a deflection instead of guessing."""
from __future__ import annotations

from rag.vector_store import VectorStore


def retrieve_context(query: str, store: VectorStore, k: int = 4, min_score: float = 0.25) -> str | None:
    results = store.search(query, k=k)
    matches = [text for text, _meta, score in results if score >= min_score]
    if not matches:
        return None
    return "\n---\n".join(matches)
