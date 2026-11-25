"""SchemeSaathi AI — Document chunker for RAG ingestion.

Splits cleaned text into 400–600 token chunks with ~80-token overlap,
splitting preferably at heading boundaries.  Each chunk carries
metadata for later retrieval filtering and citation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Chunk data class ─────────────────────────────────────────────


@dataclass
class Chunk:
    """A single text chunk with provenance metadata."""

    text: str
    chunk_index: int
    scheme_id: Optional[int] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    page: Optional[int] = None
    language: str = "en"
    verified_date: Optional[str] = None
    doc_type: str = "unknown"          # pdf | html | json

    # Set after embedding
    embedding: list[float] = field(default_factory=list, repr=False)

    def to_metadata(self) -> dict:
        """Return metadata dict (everything except text and embedding)."""
        d = asdict(self)
        d.pop("text", None)
        d.pop("embedding", None)
        return d


# ── Approximate token counter ───────────────────────────────────


def _approx_tokens(text: str) -> int:
    """Rough token count — 1 token ≈ 4 chars for English, 2 for Indic."""
    return max(1, len(text) // 4)


# ── Heading-aware paragraph splitter ────────────────────────────


_HEADING_RE = re.compile(
    r"^(?:#{1,4}\s|(?:CHAPTER|SECTION|PART|SCHEDULE)\b)",
    re.IGNORECASE | re.MULTILINE,
)


def _split_at_headings(text: str) -> list[str]:
    """Split text at markdown-style headings or document section headings."""
    parts = _HEADING_RE.split(text)
    markers = _HEADING_RE.findall(text)

    result = []
    if parts and parts[0].strip():
        result.append(parts[0].strip())

    for marker, body in zip(markers, parts[1:]):
        combined = (marker + body).strip()
        if combined:
            result.append(combined)

    return result if result else [text]


# ── Core chunking function ──────────────────────────────────────


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 80,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Split *text* into overlapping chunks of ~chunk_size tokens.

    Parameters
    ----------
    text : str
        Cleaned document text.
    chunk_size : int
        Target tokens per chunk (400–600 recommended).
    chunk_overlap : int
        Overlap tokens between consecutive chunks.
    metadata : dict, optional
        Base metadata applied to every chunk (scheme_id, source_url, etc.).

    Returns
    -------
    list[Chunk]
    """
    if not text or not text.strip():
        return []

    metadata = metadata or {}
    sections = _split_at_headings(text)

    paragraphs: list[str] = []
    for section in sections:
        for para in section.split("\n\n"):
            stripped = para.strip()
            if stripped:
                paragraphs.append(stripped)

    chunks: list[Chunk] = []
    current_text = ""
    chunk_index = 0

    for para in paragraphs:
        candidate = (current_text + "\n\n" + para).strip() if current_text else para
        if _approx_tokens(candidate) > chunk_size and current_text:
            # Flush current chunk
            chunks.append(
                Chunk(
                    text=current_text,
                    chunk_index=chunk_index,
                    **{k: v for k, v in metadata.items() if k in Chunk.__dataclass_fields__},
                )
            )
            chunk_index += 1

            # Overlap: keep tail of current_text
            overlap_chars = chunk_overlap * 4
            overlap_text = current_text[-overlap_chars:] if len(current_text) > overlap_chars else current_text
            current_text = (overlap_text + "\n\n" + para).strip()
        else:
            current_text = candidate

    # Final chunk
    if current_text.strip():
        chunks.append(
            Chunk(
                text=current_text,
                chunk_index=chunk_index,
                **{k: v for k, v in metadata.items() if k in Chunk.__dataclass_fields__},
            )
        )

    return chunks
