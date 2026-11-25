"""SchemeSaathi AI — FAISS-backed vector store for RAG.

Manages a FAISS flat-IP index on L2-normalised vectors (= cosine similarity)
plus a parallel JSON metadata file.  Supports add, search, save, and load.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

import numpy as np

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.rag.chunker import Chunk


class VectorStore:
    """Thin wrapper around a FAISS IndexFlatIP with metadata side-car."""

    def __init__(self, dimension: int = 768):
        import faiss

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: list[dict] = []
        self.texts: list[str] = []

    # ── Add ───────────────────────────────────────────────────────

    def add_chunks(self, chunks: list[Chunk]) -> int:
        """Add embedded chunks to the index.

        Returns the number of vectors added.
        """
        vectors = []
        for chunk in chunks:
            if not chunk.embedding:
                logger.warning("Skipping chunk %d — no embedding", chunk.chunk_index)
                continue
            vectors.append(chunk.embedding)
            self.metadata.append(chunk.to_metadata())
            self.texts.append(chunk.text)

        if not vectors:
            return 0

        arr = np.array(vectors, dtype=np.float32)
        # L2-normalise so inner product == cosine similarity
        import faiss
        faiss.normalize_L2(arr)
        self.index.add(arr)

        logger.info("Added %d vectors (total: %d)", len(vectors), self.index.ntotal)
        return len(vectors)

    # ── Search ───────────────────────────────────────────────────

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 6,
        filters: dict | None = None,
    ) -> list[dict]:
        """Return top-k results as dicts with text, metadata, and score.

        Parameters
        ----------
        query_embedding : list[float]
            The query vector (will be L2-normalised internally).
        top_k : int
            Number of results.
        filters : dict, optional
            Key-value pairs to match against chunk metadata (e.g. ``{"language": "te"}``).
        """
        if self.index.ntotal == 0:
            return []

        import faiss

        q = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(q)

        # Retrieve more than top_k to allow for filtering
        fetch_k = min(top_k * 4, self.index.ntotal)
        scores, indices = self.index.search(q, fetch_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]

            # Apply filters
            if filters and not all(meta.get(k) == v for k, v in filters.items()):
                continue

            results.append({
                "text": self.texts[idx],
                "metadata": meta,
                "score": float(score),
            })
            if len(results) >= top_k:
                break

        return results

    # ── Persistence ──────────────────────────────────────────────

    def save(self, index_path: str, metadata_path: str) -> None:
        """Save FAISS index and metadata to disk."""
        import faiss

        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        faiss.write_index(self.index, index_path)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(
                {"metadata": self.metadata, "texts": self.texts},
                f,
                ensure_ascii=False,
            )
        logger.info(
            "Saved index (%d vectors) to %s", self.index.ntotal, index_path
        )

    @classmethod
    def load(cls, index_path: str, metadata_path: str) -> VectorStore:
        """Load a previously saved index."""
        import faiss

        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            raise FileNotFoundError(
                f"Index files not found: {index_path}, {metadata_path}"
            )

        index = faiss.read_index(index_path)
        store = cls(dimension=index.d)
        store.index = index

        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            store.metadata = data["metadata"]
            store.texts = data["texts"]

        logger.info("Loaded index with %d vectors", store.index.ntotal)
        return store

    @classmethod
    def load_or_create(
        cls, index_path: str, metadata_path: str, dimension: int = 768
    ) -> VectorStore:
        """Load an existing index or create a new empty one."""
        try:
            return cls.load(index_path, metadata_path)
        except FileNotFoundError:
            logger.info("No existing index found — creating new empty store.")
            return cls(dimension=dimension)
