"""Turns the demo project JSON and uploaded PDFs into short text chunks for the
vector store. Deliberately simple — a fixed-size splitter is enough at this scale."""
from __future__ import annotations

import logging

from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50


def load_demo_project_as_documents(project: dict) -> list[str]:
    docs = [
        f"{project.get('project_name')} is located at {project.get('location')}. "
        f"Configurations available: {', '.join(project.get('property_types', []))}. "
        f"Price range: {project.get('price_range', {}).get('display')}. "
        f"Possession: {project.get('possession')}. RERA number: {project.get('rera_number')}.",
        f"Amenities at {project.get('project_name')}: " + ", ".join(project.get("amenities", [])) + ".",
    ]
    for row in project.get("inventory", []):
        docs.append(
            f"{row.get('config')} at {project.get('project_name')}: {row.get('size_sqft')} sqft, "
            f"priced at ₹{row.get('price'):,}, with {row.get('units_available')} units currently available."
        )
    for faq in project.get("faqs", []):
        docs.append(f"Q: {faq.get('question')} A: {faq.get('answer')}")
    return docs


def chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def ingest_pdf(file_bytes: bytes) -> list[str]:
    from pypdf import PdfReader
    from io import BytesIO

    reader = PdfReader(BytesIO(file_bytes))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if not full_text.strip():
        return []
    return chunk_text(full_text)


def build_index(chunks: list[str], source: str, store: VectorStore) -> None:
    if not chunks:
        return
    metadatas = [{"source": source} for _ in chunks]
    store.add(chunks, metadatas)
    store.save()
