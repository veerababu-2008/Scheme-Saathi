"""SchemeSaathi AI — RAG pipeline unit tests.

Tests the cleaner, chunker, prompt builder, validator, and vector store
without requiring the Gemini API (mocked where needed).
"""

import pytest
import numpy as np

from app.services.rag.cleaner import (
    clean_text,
    normalise_unicode,
    collapse_whitespace,
    remove_boilerplate,
    normalise_rupee,
)
from app.services.rag.chunker import chunk_text, Chunk, _approx_tokens
from app.services.rag.prompt import (
    detect_language,
    build_context_block,
    build_messages,
    extract_citations,
    SYSTEM_PROMPT,
)
from app.services.rag.validator import (
    validate_response,
    build_fallback_response,
)


# ══════════════════════════════════════════════════════════════════
# CLEANER TESTS
# ══════════════════════════════════════════════════════════════════


class TestCleaner:
    """Tests for text cleaning functions."""

    def test_normalise_unicode_nfc(self):
        # Devanagari क + ◌ा  vs  का  (pre-composed)
        decomposed = "\u0915\u093E"  # क + ◌ा
        result = normalise_unicode(decomposed)
        assert result == "का"

    def test_collapse_whitespace(self):
        text = "hello   world\n\n\n\n\nparagraph two"
        result = collapse_whitespace(text)
        assert "   " not in result
        assert "\n\n\n" not in result
        assert "hello world" in result

    def test_remove_boilerplate_page_numbers(self):
        text = "Some content\nPage 3 of 10\nMore content"
        result = remove_boilerplate(text)
        assert "Page 3 of 10" not in result
        assert "Some content" in result

    def test_remove_boilerplate_bare_numbers(self):
        text = "content\n  42  \nmore content"
        result = remove_boilerplate(text)
        assert result.strip() != ""

    def test_normalise_rupee_rs(self):
        assert "₹5,000" in normalise_rupee("Rs. 5,000")
        assert "₹5,000" in normalise_rupee("Rs 5,000")

    def test_normalise_rupee_inr(self):
        assert "₹" in normalise_rupee("INR 10,000")

    def test_clean_text_full_pipeline(self):
        raw = "  Page 1 of 5  \n\nRs. 6000 benefit\n\n\n\n\nMore info  "
        result = clean_text(raw)
        assert "Page 1 of 5" not in result
        assert "₹6000" in result
        assert "\n\n\n" not in result

    def test_clean_text_empty(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""


# ══════════════════════════════════════════════════════════════════
# CHUNKER TESTS
# ══════════════════════════════════════════════════════════════════


class TestChunker:
    """Tests for the document chunker."""

    def test_approx_tokens(self):
        # ~25 chars → ~6 tokens
        assert _approx_tokens("hello world test string!") >= 1

    def test_chunk_empty_text(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_chunk_short_text(self):
        text = "This is a short paragraph."
        chunks = chunk_text(text, chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].chunk_index == 0

    def test_chunk_with_metadata(self):
        text = "Some scheme description."
        chunks = chunk_text(
            text,
            metadata={
                "scheme_id": 42,
                "source_url": "https://example.com",
                "language": "en",
            },
        )
        assert len(chunks) == 1
        assert chunks[0].scheme_id == 42
        assert chunks[0].source_url == "https://example.com"
        assert chunks[0].language == "en"

    def test_chunk_long_text_produces_multiple_chunks(self):
        # ~200 tokens per paragraph × 5 paragraphs = ~1000 tokens
        para = "word " * 200
        text = "\n\n".join([para] * 5)
        chunks = chunk_text(text, chunk_size=300, chunk_overlap=50)
        assert len(chunks) > 1

    def test_chunk_metadata_to_dict(self):
        c = Chunk(
            text="hello",
            chunk_index=0,
            scheme_id=1,
            source_title="Test",
            language="te",
        )
        meta = c.to_metadata()
        assert "text" not in meta
        assert "embedding" not in meta
        assert meta["scheme_id"] == 1
        assert meta["language"] == "te"

    def test_chunk_heading_splitting(self):
        text = "# Section One\nContent here.\n\n# Section Two\nMore content."
        chunks = chunk_text(text, chunk_size=500)
        # With a large chunk_size, may be 1 chunk, but heading splitting works
        assert len(chunks) >= 1
        assert any("Content here" in c.text for c in chunks)


# ══════════════════════════════════════════════════════════════════
# PROMPT TESTS
# ══════════════════════════════════════════════════════════════════


class TestPrompt:
    """Tests for prompt construction and language detection."""

    def test_detect_language_english(self):
        assert detect_language("What is PM-KISAN?") == "en"

    def test_detect_language_telugu(self):
        assert detect_language("పీఎం-కిసాన్ అంటే ఏమిటి?") == "te"

    def test_detect_language_hindi(self):
        assert detect_language("पीएम-किसान क्या है?") == "hi"

    def test_detect_language_mixed_telugu_first(self):
        assert detect_language("Tell me about పథకం") == "te"

    def test_build_context_block_empty(self):
        result = build_context_block([])
        assert "No relevant documents" in result

    def test_build_context_block_with_chunks(self):
        chunks = [
            {
                "text": "PM-KISAN provides ₹6,000 per year.",
                "metadata": {"source_title": "PM-KISAN Portal"},
                "score": 0.92,
            }
        ]
        result = build_context_block(chunks)
        assert "PM-KISAN Portal" in result
        assert "0.92" in result
        assert "₹6,000" in result

    def test_build_messages_basic(self):
        chunks = [
            {
                "text": "Some context.",
                "metadata": {"source_title": "Test"},
                "score": 0.5,
            }
        ]
        messages = build_messages("What is PMAY?", chunks)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "What is PMAY?" in messages[0]["parts"][0]
        assert "Some context." in messages[0]["parts"][0]

    def test_build_messages_with_history(self):
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        messages = build_messages("Follow up", [], history)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "model"
        assert messages[2]["role"] == "user"

    def test_build_messages_history_limit(self):
        # More than 10 history messages → only last 10 kept
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(20)
        ]
        messages = build_messages("Current question", [], history)
        # 10 history + 1 current = 11
        assert len(messages) == 11

    def test_extract_citations(self):
        chunks = [
            {
                "text": "...",
                "metadata": {
                    "source_title": "PM-KISAN Portal",
                    "source_url": "https://pmkisan.gov.in",
                    "scheme_id": 1,
                    "verified_date": None,
                },
                "score": 0.9,
            },
            {
                "text": "...",
                "metadata": {
                    "source_title": "PM-KISAN Portal",
                    "source_url": "https://pmkisan.gov.in",
                    "scheme_id": 1,
                    "verified_date": None,
                },
                "score": 0.8,
            },
        ]
        citations = extract_citations(chunks)
        # Deduped
        assert len(citations) == 1
        assert citations[0]["source_title"] == "PM-KISAN Portal"

    def test_extract_citations_empty(self):
        assert extract_citations([]) == []

    def test_system_prompt_contains_key_rules(self):
        assert "not an official government portal" in SYSTEM_PROMPT.lower()
        assert "citation" in SYSTEM_PROMPT.lower() or "cite" in SYSTEM_PROMPT.lower()


# ══════════════════════════════════════════════════════════════════
# VALIDATOR TESTS
# ══════════════════════════════════════════════════════════════════


class TestValidator:
    """Tests for the response validator."""

    def test_valid_response_with_citation_and_disclaimer(self):
        answer = (
            "PM-KISAN provides ₹6,000 per year [Source: PM-KISAN Portal]. "
            "This information is for guidance only. SchemeSaathi is not an "
            "official government portal. Please verify details."
        )
        result = validate_response(answer, had_context=True)
        assert result["valid"] is True
        assert result["needs_disclaimer"] is False
        assert len(result["errors"]) == 0

    def test_missing_citation_warning(self):
        answer = "PM-KISAN provides ₹6,000 per year."
        result = validate_response(answer, had_context=True)
        assert result["valid"] is True  # warning, not error
        assert any("citation" in w.lower() for w in result["warnings"])

    def test_no_citation_warning_without_context(self):
        answer = "I don't have information about that."
        result = validate_response(answer, had_context=False)
        # No citation warning when no context was provided
        assert not any("citation" in w.lower() for w in result["warnings"])

    def test_pii_detection_aadhaar(self):
        answer = "Your Aadhaar number 1234 5678 9012 is valid."
        result = validate_response(answer)
        assert result["valid"] is False
        assert any("personal" in e.lower() for e in result["errors"])

    def test_pii_detection_pan(self):
        answer = "PAN: ABCDE1234F is linked."
        result = validate_response(answer)
        assert result["valid"] is False

    def test_needs_disclaimer(self):
        answer = "Some answer without disclaimer."
        result = validate_response(answer)
        assert result["needs_disclaimer"] is True

    def test_fabrication_warning(self):
        answer = "As per our records, you are eligible."
        result = validate_response(answer)
        assert any("fabrication" in w.lower() for w in result["warnings"])

    def test_fallback_response_en(self):
        fb = build_fallback_response("en")
        assert "not an official government portal" in fb.lower()

    def test_fallback_response_te(self):
        fb = build_fallback_response("te")
        assert "SchemeSaathi" in fb

    def test_fallback_response_hi(self):
        fb = build_fallback_response("hi")
        assert "SchemeSaathi" in fb

    def test_fallback_response_unknown_lang(self):
        fb = build_fallback_response("fr")
        # Falls back to English
        assert "not an official government portal" in fb.lower()


# ══════════════════════════════════════════════════════════════════
# VECTOR STORE TESTS
# ══════════════════════════════════════════════════════════════════


class TestVectorStore:
    """Tests for the FAISS vector store (no Gemini API needed)."""

    def test_create_empty_store(self):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore(dimension=8)
        assert store.index.ntotal == 0

    def test_add_and_search(self):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore(dimension=8)
        chunks = [
            Chunk(
                text="PM-KISAN provides income support to farmers.",
                chunk_index=0,
                scheme_id=1,
                source_title="PM-KISAN",
                language="en",
                embedding=list(np.random.rand(8).astype(float)),
            ),
            Chunk(
                text="PMAY provides housing assistance.",
                chunk_index=1,
                scheme_id=2,
                source_title="PMAY",
                language="en",
                embedding=list(np.random.rand(8).astype(float)),
            ),
        ]
        added = store.add_chunks(chunks)
        assert added == 2
        assert store.index.ntotal == 2

        query_vec = list(np.random.rand(8).astype(float))
        results = store.search(query_vec, top_k=2)
        assert len(results) == 2
        assert "text" in results[0]
        assert "metadata" in results[0]
        assert "score" in results[0]

    def test_search_with_filter(self):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore(dimension=4)

        # Use deterministic vectors
        chunks = [
            Chunk(
                text="English text about KISAN.",
                chunk_index=0,
                language="en",
                embedding=[1.0, 0.0, 0.0, 0.0],
            ),
            Chunk(
                text="తెలుగు వచనం.",
                chunk_index=1,
                language="te",
                embedding=[0.0, 1.0, 0.0, 0.0],
            ),
        ]
        store.add_chunks(chunks)

        # Filter to Telugu only
        results = store.search(
            [0.5, 0.5, 0.0, 0.0], top_k=2, filters={"language": "te"}
        )
        assert len(results) == 1
        assert results[0]["metadata"]["language"] == "te"

    def test_search_empty_store(self):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore(dimension=4)
        results = store.search([1.0, 0.0, 0.0, 0.0], top_k=5)
        assert results == []

    def test_save_and_load(self, tmp_path):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore(dimension=4)
        chunks = [
            Chunk(
                text="Test document.",
                chunk_index=0,
                source_title="Test",
                embedding=[1.0, 0.0, 0.0, 0.0],
            ),
        ]
        store.add_chunks(chunks)

        idx_file = str(tmp_path / "test.idx")
        meta_file = str(tmp_path / "test_meta.json")
        store.save(idx_file, meta_file)

        loaded = VectorStore.load(idx_file, meta_file)
        assert loaded.index.ntotal == 1
        assert loaded.texts[0] == "Test document."
        assert loaded.metadata[0]["source_title"] == "Test"

    def test_load_or_create_nonexistent(self, tmp_path):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore.load_or_create(
            str(tmp_path / "nope.idx"),
            str(tmp_path / "nope.json"),
            dimension=4,
        )
        assert store.index.ntotal == 0

    def test_skip_chunks_without_embedding(self):
        from app.services.rag.vector_store import VectorStore

        store = VectorStore(dimension=4)
        chunks = [
            Chunk(text="No embedding", chunk_index=0),
        ]
        added = store.add_chunks(chunks)
        assert added == 0


# ══════════════════════════════════════════════════════════════════
# INGEST TESTS (scheme seed extraction, no Gemini API)
# ══════════════════════════════════════════════════════════════════


class TestIngestExtraction:
    """Tests for scheme-seed extraction (no API calls needed)."""

    def test_extract_scheme_texts(self, tmp_path):
        import json
        from app.services.rag.ingest import extract_scheme_texts

        schemes = [
            {
                "name": "Test Scheme",
                "name_te": "పరీక్ష పథకం",
                "name_hi": "परीक्षा योजना",
                "slug": "test-scheme",
                "description": "A test scheme for farmers.",
                "description_te": "రైతుల కోసం పరీక్ష పథకం.",
                "description_hi": "किसानों के लिए परीक्षा योजना।",
                "benefits": "₹5,000 per year.",
                "benefits_te": "సంవత్సరానికి ₹5,000.",
                "benefits_hi": "₹5,000 प्रति वर्ष।",
                "level": "central",
                "state": None,
                "department": "Agriculture",
                "ministry": "MoA",
                "official_url": "https://example.gov.in",
                "documents": [
                    {"document_name": "Aadhaar Card"},
                ],
                "sources": [
                    {"title": "Official Portal", "url": "https://example.gov.in"},
                ],
            }
        ]
        path = tmp_path / "schemes.json"
        path.write_text(json.dumps(schemes), encoding="utf-8")

        docs = extract_scheme_texts(str(path))
        # 1 English + 1 Telugu + 1 Hindi = 3
        assert len(docs) == 3

        en_doc = docs[0]
        assert "Test Scheme" in en_doc["text"]
        assert en_doc["metadata"]["language"] == "en"
        assert en_doc["metadata"]["source_url"] == "https://example.gov.in"

        te_doc = docs[1]
        assert te_doc["metadata"]["language"] == "te"

        hi_doc = docs[2]
        assert hi_doc["metadata"]["language"] == "hi"

    def test_extract_scheme_texts_no_translations(self, tmp_path):
        import json
        from app.services.rag.ingest import extract_scheme_texts

        schemes = [
            {
                "name": "English Only Scheme",
                "slug": "en-only",
                "description": "English description.",
                "benefits": "Some benefits.",
                "level": "state",
                "state": "Telangana",
                "department": "Dept",
                "ministry": None,
                "official_url": None,
                "documents": [],
                "sources": [],
            }
        ]
        path = tmp_path / "schemes2.json"
        path.write_text(json.dumps(schemes), encoding="utf-8")

        docs = extract_scheme_texts(str(path))
        # Only English (no te/hi descriptions)
        assert len(docs) == 1
        assert "Telangana" in docs[0]["text"]
