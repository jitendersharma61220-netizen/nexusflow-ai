"""Minimal local FAISS vector store — no server, no paid vector DB. Two files
(`index.faiss` + `meta.pkl`) are enough for a single project's knowledge base."""
from __future__ import annotations

import logging
import os
import pickle
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

_EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_DIM = 384


@lru_cache(maxsize=1)
def _get_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_EMBED_MODEL_NAME)


class VectorStore:
    def __init__(self, dim: int = _DIM, index_path: str = "data/local_store/faiss_index"):
        import faiss

        self._dim = dim
        self._index_path = index_path
        self._meta_path = index_path + ".meta.pkl"
        self._index = faiss.IndexFlatIP(dim)
        self._meta: list[tuple[str, dict]] = []

    def add(self, texts: list[str], metadatas: list[dict]) -> None:
        if not texts:
            return
        embeddings = self._embed(texts)
        self._index.add(embeddings)
        self._meta.extend(zip(texts, metadatas))

    def search(self, query: str, k: int = 4) -> list[tuple[str, dict, float]]:
        if self._index.ntotal == 0:
            return []
        query_vec = self._embed([query])
        scores, indices = self._index.search(query_vec, min(k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            text, meta = self._meta[idx]
            results.append((text, meta, float(score)))
        return results

    def save(self) -> None:
        import faiss

        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        faiss.write_index(self._index, self._index_path)
        with open(self._meta_path, "wb") as f:
            pickle.dump(self._meta, f)

    def load(self) -> bool:
        import faiss

        if not (os.path.exists(self._index_path) and os.path.exists(self._meta_path)):
            return False
        try:
            self._index = faiss.read_index(self._index_path)
            with open(self._meta_path, "rb") as f:
                self._meta = pickle.load(f)
            return True
        except Exception:
            logger.exception("Failed to load FAISS index — will rebuild")
            return False

    def _embed(self, texts: list[str]) -> np.ndarray:
        embedder = _get_embedder()
        vectors = embedder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.astype("float32")
