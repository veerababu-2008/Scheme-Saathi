"""SchemeSaathi AI — Thin Gemini API client.

Wraps Google's Generative AI SDK for chat-completion calls.
All Gemini interactions go through this module so rate-limiting,
error handling, and privacy filtering live in one place.

Privacy rule: NEVER send user names, phone numbers, emails, or
Aadhaar-like numbers to the Gemini API.  Only age band, state,
occupation, and similar anonymised fields are allowed.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ── PII scrubber ─────────────────────────────────────────────────

_PII_PATTERNS = [
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[REDACTED_ID]"),
    (re.compile(r"\b\d{10}\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[REDACTED_PAN]"),
]


def _scrub_pii(text: str) -> str:
    """Remove personally identifiable information from text."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── Client ───────────────────────────────────────────────────────

_model_instance = None


def _get_model():
    """Lazy-initialise the Gemini generative model."""
    global _model_instance
    if _model_instance is None:
        import google.generativeai as genai
        from flask import current_app

        api_key = current_app.config["GEMINI_API_KEY"]
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Please add it to your .env file."
            )

        genai.configure(api_key=api_key)
        model_name = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
        _model_instance = genai.GenerativeModel(
            model_name,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.85,
                "max_output_tokens": 2048,
            },
        )
    return _model_instance


def generate_chat_response(
    messages: list[dict],
    system_prompt: str,
    *,
    temperature: float | None = None,
) -> str:
    """Send messages to Gemini and return the response text.

    Parameters
    ----------
    messages : list[dict]
        Messages in ``[{"role": "user"|"model", "parts": ["..."]}]`` format.
    system_prompt : str
        The system-level instructions.
    temperature : float, optional
        Override the default temperature.

    Returns
    -------
    str
        The model's response text.
    """
    model = _get_model()

    # Scrub PII from all user messages
    cleaned_messages = []
    for msg in messages:
        parts = [_scrub_pii(p) if isinstance(p, str) else p for p in msg["parts"]]
        cleaned_messages.append({"role": msg["role"], "parts": parts})

    try:
        chat = model.start_chat(history=cleaned_messages[:-1])

        gen_config = {}
        if temperature is not None:
            gen_config["temperature"] = temperature

        response = chat.send_message(
            cleaned_messages[-1]["parts"],
            generation_config=gen_config if gen_config else None,
        )

        return response.text

    except Exception as e:
        logger.error("Gemini API error: %s", str(e))
        raise GeminiError(str(e)) from e


class GeminiError(Exception):
    """Raised when the Gemini API returns an error."""
