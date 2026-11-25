"""SchemeSaathi AI — System prompt templates and context builder for Saathi AI.

Assembles the system prompt, context chunks, and user query into the
final message payload sent to Gemini.  Includes citation rules, language
detection, and the mandatory disclaimer.
"""

from __future__ import annotations

# ── System prompt template ───────────────────────────────────────

SYSTEM_PROMPT = """You are **Saathi**, a helpful and empathetic AI assistant for SchemeSaathi, \
a civic-tech platform that helps Indian citizens understand government welfare schemes.

## Your Role
- Help citizens understand government scheme eligibility, required documents, benefits, and application processes.
- Speak in the user's language (English, Telugu, or Hindi). Detect the user's language from their message and respond in the same language.
- Be warm, respectful, and use simple everyday language. Avoid legal jargon.

## Strict Rules
1. **ONLY use the provided context** to answer questions. If the context does not contain enough information, say so clearly — do NOT guess or invent information.
2. **NEVER fabricate** scheme names, benefit amounts, eligibility criteria, or deadlines.
3. **ALWAYS cite sources.** For every factual claim, include a citation in the format [Source: <source_title>]. If multiple sources support a point, cite all.
4. **Disclaimer:** Always end your response with:
   "⚠️ This information is for guidance only. SchemeSaathi is not an official government portal. Please verify details at the official scheme website or your nearest government office."
5. **Privacy:** NEVER ask for or reference Aadhaar numbers, bank account numbers, phone numbers, or any personal identification numbers.
6. If you do not know the answer, say: "I don't have enough verified information to answer this question. Please check the official scheme website or visit your nearest government office."
7. When describing eligibility, make clear this is **informational guidance**, not an official determination.

## Response Format
- Use clear headings and bullet points for readability.
- Keep answers concise but complete.
- For scheme comparisons, use a structured format.
- Currency amounts should use ₹ symbol.
"""

# ── Disclaimer (appended when validator detects it's missing) ────

DISCLAIMER_TEXT = (
    "\n\n⚠️ *This information is for guidance only. SchemeSaathi is not an "
    "official government portal. Please verify details at the official scheme "
    "website or your nearest government office.*"
)

# ── Language detection hints ─────────────────────────────────────

_TELUGU_RANGE = range(0x0C00, 0x0C80)
_DEVANAGARI_RANGE = range(0x0900, 0x0980)


def detect_language(text: str) -> str:
    """Detect language from script: te (Telugu), hi (Hindi/Devanagari), en (default)."""
    for ch in text:
        code = ord(ch)
        if code in _TELUGU_RANGE:
            return "te"
        if code in _DEVANAGARI_RANGE:
            return "hi"
    return "en"


# ── Context builder ──────────────────────────────────────────────


def build_context_block(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the prompt.

    Parameters
    ----------
    chunks : list[dict]
        Results from the retriever (each has ``text``, ``metadata``, ``score``).

    Returns
    -------
    str
        Formatted context ready for insertion into the prompt.
    """
    if not chunks:
        return "(No relevant documents found in the knowledge base.)"

    lines = ["## Retrieved Context\n"]
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source_title", "Unknown source")
        score = chunk.get("score", 0.0)
        lines.append(f"### [{i}] {source} (relevance: {score:.2f})")
        lines.append(chunk["text"])
        lines.append("")  # blank line

    return "\n".join(lines)


def build_messages(
    user_query: str,
    context_chunks: list[dict],
    chat_history: list[dict] | None = None,
) -> list[dict]:
    """Assemble the message list for the Gemini API.

    Parameters
    ----------
    user_query : str
        The user's current message.
    context_chunks : list[dict]
        Retrieved context chunks.
    chat_history : list[dict], optional
        Prior messages in the session, each with ``role`` and ``content``.

    Returns
    -------
    list[dict]
        Messages in Gemini's ``[{"role": ..., "parts": ...}]`` format.
    """
    context_block = build_context_block(context_chunks)

    messages = []

    # Inject history (last 10 turns max to stay within context window)
    if chat_history:
        for msg in chat_history[-10:]:
            role = "user" if msg["role"] == "user" else "model"
            messages.append({"role": role, "parts": [msg["content"]]})

    # Current user turn with context
    user_message = (
        f"{context_block}\n\n"
        f"## User Question\n{user_query}"
    )
    messages.append({"role": "user", "parts": [user_message]})

    return messages


def extract_citations(context_chunks: list[dict]) -> list[dict]:
    """Extract citation metadata from context chunks.

    Returns a list of citation dicts for storage alongside the
    assistant's response.
    """
    citations = []
    seen_sources = set()
    for chunk in context_chunks:
        meta = chunk.get("metadata", {})
        source_title = meta.get("source_title", "")
        source_url = meta.get("source_url", "")
        key = (source_title, source_url)
        if key not in seen_sources and source_title:
            seen_sources.add(key)
            citations.append({
                "source_title": source_title,
                "source_url": source_url,
                "scheme_id": meta.get("scheme_id"),
                "verified_date": meta.get("verified_date"),
            })
    return citations
