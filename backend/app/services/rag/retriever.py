"""SchemeSaathi AI — RAG retriever: query → relevant chunks.

Ties together the vector store, embeddings, and optional metadata
filters to return the top-k most relevant chunks for a user query.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Module-level store singleton (loaded once per process)
_store = None


def _get_store():
    """Lazy-load the FAISS vector store."""
    global _store
    if _store is None:
        from flask import current_app

        from app.services.rag.vector_store import VectorStore

        idx_path = current_app.config["FAISS_INDEX_PATH"]
        meta_path = current_app.config["FAISS_METADATA_PATH"]
        _store = VectorStore.load_or_create(idx_path, meta_path)
    return _store


def reset_store() -> None:
    """Reset the cached store (useful after re-ingestion)."""
    global _store
    _store = None


def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    language: str | None = None,
    scheme_id: int | None = None,
) -> list[dict]:
    """Retrieve the most relevant chunks for *query*.

    Parameters
    ----------
    query : str
        User's natural-language question.
    top_k : int, optional
        Override the configured RAG_TOP_K.
    language : str, optional
        Filter to chunks in this language (``en``, ``te``, ``hi``).
    scheme_id : int, optional
        Filter to chunks from a specific scheme.

    Returns
    -------
    list[dict]
        Each dict has keys: ``text``, ``metadata``, ``score``.
    """
    from flask import current_app

    from app.services.rag.embeddings import embed_query

    if top_k is None:
        top_k = current_app.config.get("RAG_TOP_K", 6)

    store = _get_store()

    if store.index.ntotal == 0:
        logger.warning("Vector store is empty — no documents ingested yet.")
        return []

    query_embedding = embed_query(query)

    filters = {}
    if language:
        filters["language"] = language
    if scheme_id is not None:
        filters["scheme_id"] = scheme_id

    results = store.search(
        query_embedding,
        top_k=top_k,
        filters=filters if filters else None,
    )

    logger.info(
        "Retrieved %d chunks for query (top_k=%d, filters=%s)",
        len(results), top_k, filters or "none",
    )
    return results
