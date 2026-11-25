"""SchemeSaathi AI — Gemini embedding wrapper for RAG.

Wraps Google's Generative AI embedding endpoint to produce vectors
for both ingestion (document chunks) and query-time retrieval.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.rag.chunker import Chunk

logger = logging.getLogger(__name__)

# Lazy-loaded client
_model = None


def _get_model():
    """Return the Gemini embedding model (lazy init)."""
    global _model
    if _model is None:
        import google.generativeai as genai
        from flask import current_app

        genai.configure(api_key=current_app.config["GEMINI_API_KEY"])
        _model = current_app.config["GEMINI_EMBEDDING_MODEL"]
    return _model


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single text string.

    Parameters
    ----------
    text : str
        The text to embed.
    task_type : str
        One of ``RETRIEVAL_DOCUMENT`` (indexing) or ``RETRIEVAL_QUERY`` (search).

    Returns
    -------
    list[float]
        Embedding vector.
    """
    import google.generativeai as genai

    model_name = _get_model()
    result = genai.embed_content(
        model=model_name,
        content=text,
        task_type=task_type,
    )
    return result["embedding"]


def embed_query(query: str) -> list[float]:
    """Embed a user query for retrieval."""
    return embed_text(query, task_type="RETRIEVAL_QUERY")


def embed_chunks(
    chunks: list[Chunk],
    *,
    batch_size: int = 20,
    delay: float = 0.5,
) -> list[Chunk]:
    """Embed a list of Chunks in batches, respecting rate limits.

    Mutates each chunk in-place by setting ``chunk.embedding``.
    Returns the same list for chaining convenience.
    """
    import google.generativeai as genai

    model_name = _get_model()
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.text for c in batch]

        result = genai.embed_content(
            model=model_name,
            content=texts,
            task_type="RETRIEVAL_DOCUMENT",
        )
        embeddings = result["embedding"]

        for chunk, emb in zip(batch, embeddings, strict=False):
            chunk.embedding = emb

        logger.info(
            "Embedded batch %d–%d of %d chunks",
            i + 1, min(i + batch_size, total), total,
        )
        if i + batch_size < total:
            time.sleep(delay)

    return chunks
