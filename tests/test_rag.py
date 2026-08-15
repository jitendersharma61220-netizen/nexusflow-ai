import pytest

from rag.retriever import retrieve_context
from rag.vector_store import VectorStore


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    index_path = str(tmp_path_factory.mktemp("faiss") / "index")
    vs = VectorStore(index_path=index_path)
    vs.add(
        texts=[
            "Nexus Heights is located at Golf Course Road, Gurgaon.",
            "The clubhouse includes a swimming pool, gym, and kids play area.",
            "2 BHK units are priced at 1.45 Cr with 1250 sqft.",
        ],
        metadatas=[{"source": "demo"}] * 3,
    )
    return vs


def test_retrieve_matching_query_returns_context(store):
    context = retrieve_context("What amenities does the clubhouse have?", store, min_score=0.1)
    assert context is not None
    assert "clubhouse" in context.lower() or "pool" in context.lower()


def test_retrieve_off_topic_query_returns_none(store):
    context = retrieve_context("What is the capital of France?", store, min_score=0.5)
    assert context is None


def test_empty_store_returns_none(tmp_path):
    empty_store = VectorStore(index_path=str(tmp_path / "empty_index"))
    context = retrieve_context("anything", empty_store)
    assert context is None
