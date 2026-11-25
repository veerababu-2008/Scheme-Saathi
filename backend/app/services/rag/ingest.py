"""SchemeSaathi AI — Document ingestion pipeline for RAG.

Supports:
- PDF ingestion (via pdfplumber)
- HTML ingestion (via trafilatura)
- JSON scheme-seed ingestion (from seeds/schemes.json)

Each source flows through: extract → clean → chunk → embed → store.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


# ── PDF extraction ───────────────────────────────────────────────


def extract_pdf(filepath: str) -> list[dict]:
    """Extract text from a PDF, one entry per page.

    Returns list of ``{"text": ..., "page": int}``.
    """
    import pdfplumber

    pages = []
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"text": text, "page": i})
    logger.info("Extracted %d pages from %s", len(pages), filepath)
    return pages


# ── HTML extraction ──────────────────────────────────────────────


def extract_html(filepath: str) -> str:
    """Extract main content from an HTML file using trafilatura."""
    import trafilatura

    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    text = trafilatura.extract(raw) or ""
    logger.info(
        "Extracted %d chars from HTML %s", len(text), filepath
    )
    return text


# ── Scheme-seed JSON ingestion ───────────────────────────────────


def extract_scheme_texts(schemes_json_path: str) -> list[dict]:
    """Extract textual content from the seed schemes JSON file.

    Returns one document dict per scheme with combined description,
    benefits, and eligibility info.
    """
    with open(schemes_json_path, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    documents = []
    for scheme in schemes:
        # English
        parts = [
            f"Scheme: {scheme['name']}",
            f"Level: {scheme['level']}",
        ]
        if scheme.get("state"):
            parts.append(f"State: {scheme['state']}")
        if scheme.get("department"):
            parts.append(f"Department: {scheme['department']}")
        if scheme.get("ministry"):
            parts.append(f"Ministry: {scheme['ministry']}")
        parts.append(f"Description: {scheme['description']}")
        parts.append(f"Benefits: {scheme['benefits']}")

        # Documents required
        if scheme.get("documents"):
            docs_text = ", ".join(d["document_name"] for d in scheme["documents"])
            parts.append(f"Required Documents: {docs_text}")

        # Sources
        if scheme.get("sources"):
            for src in scheme["sources"]:
                parts.append(f"Source: {src['title']} ({src.get('url', 'N/A')})")

        documents.append({
            "text": "\n".join(parts),
            "metadata": {
                "source_title": scheme["name"],
                "source_url": scheme.get("official_url", ""),
                "language": "en",
                "doc_type": "json",
                "verified_date": None,
            },
        })

        # Telugu version
        if scheme.get("description_te"):
            te_parts = [
                f"పథకం: {scheme.get('name_te', scheme['name'])}",
                f"వివరణ: {scheme['description_te']}",
                f"ప్రయోజనాలు: {scheme.get('benefits_te', '')}",
            ]
            documents.append({
                "text": "\n".join(te_parts),
                "metadata": {
                    "source_title": scheme.get("name_te", scheme["name"]),
                    "source_url": scheme.get("official_url", ""),
                    "language": "te",
                    "doc_type": "json",
                    "verified_date": None,
                },
            })

        # Hindi version
        if scheme.get("description_hi"):
            hi_parts = [
                f"योजना: {scheme.get('name_hi', scheme['name'])}",
                f"विवरण: {scheme['description_hi']}",
                f"लाभ: {scheme.get('benefits_hi', '')}",
            ]
            documents.append({
                "text": "\n".join(hi_parts),
                "metadata": {
                    "source_title": scheme.get("name_hi", scheme["name"]),
                    "source_url": scheme.get("official_url", ""),
                    "language": "hi",
                    "doc_type": "json",
                    "verified_date": None,
                },
            })

    logger.info("Extracted %d documents from scheme seeds", len(documents))
    return documents


# ── Full ingestion pipeline ──────────────────────────────────────


def ingest_directory(
    raw_dir: str,
    schemes_json_path: str | None = None,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> int:
    """Ingest all documents from a directory into the vector store.

    Processes PDFs, HTML files, and optionally the scheme seeds JSON.
    Returns the total number of chunks indexed.

    Parameters
    ----------
    raw_dir : str
        Path to the directory containing raw documents.
    schemes_json_path : str, optional
        Path to the ``schemes.json`` seed file.
    chunk_size : int
        Target tokens per chunk.
    chunk_overlap : int
        Token overlap between chunks.
    """
    from flask import current_app

    from app.services.rag.chunker import chunk_text
    from app.services.rag.cleaner import clean_text
    from app.services.rag.embeddings import embed_chunks
    from app.services.rag.vector_store import VectorStore

    idx_path = current_app.config["FAISS_INDEX_PATH"]
    meta_path = current_app.config["FAISS_METADATA_PATH"]

    store = VectorStore.load_or_create(idx_path, meta_path)
    total_chunks = 0

    # 1. Process PDF and HTML files
    raw_path = Path(raw_dir)
    if raw_path.exists():
        for filepath in sorted(raw_path.rglob("*")):
            if filepath.suffix.lower() == ".pdf":
                pages = extract_pdf(str(filepath))
                for page_data in pages:
                    cleaned = clean_text(page_data["text"])
                    chunks = chunk_text(
                        cleaned,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        metadata={
                            "source_title": filepath.stem,
                            "source_url": "",
                            "page": page_data["page"],
                            "language": "en",
                            "doc_type": "pdf",
                        },
                    )
                    if chunks:
                        embed_chunks(chunks)
                        total_chunks += store.add_chunks(chunks)

            elif filepath.suffix.lower() in (".html", ".htm"):
                text = extract_html(str(filepath))
                cleaned = clean_text(text)
                chunks = chunk_text(
                    cleaned,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    metadata={
                        "source_title": filepath.stem,
                        "source_url": "",
                        "language": "en",
                        "doc_type": "html",
                    },
                )
                if chunks:
                    embed_chunks(chunks)
                    total_chunks += store.add_chunks(chunks)

    # 2. Process scheme seeds
    if schemes_json_path and os.path.exists(schemes_json_path):
        docs = extract_scheme_texts(schemes_json_path)
        for doc in docs:
            cleaned = clean_text(doc["text"])
            chunks = chunk_text(
                cleaned,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                metadata=doc["metadata"],
            )
            if chunks:
                embed_chunks(chunks)
                total_chunks += store.add_chunks(chunks)

    # 3. Persist the index
    store.save(idx_path, meta_path)

    # Reset the retriever's cached store
    from app.services.rag.retriever import reset_store
    reset_store()

    logger.info("Ingestion complete — %d total chunks indexed", total_chunks)
    return total_chunks
