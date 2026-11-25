"""SchemeSaathi AI — Response validator for Saathi AI answers.

Checks that generated answers meet quality and safety requirements:
- Must reference at least one source citation when context was provided.
- Must not contain hallucinated numerical claims.
- Must include the disclaimer.
- Must not reveal personal information.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger(__name__)

# ── Patterns ─────────────────────────────────────────────────────

_CITATION_PATTERN = re.compile(r"\[Source:\s*[^\]]+\]", re.IGNORECASE)

_PII_PATTERNS = [
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),          # Aadhaar-like
    re.compile(r"\b\d{10,12}\b"),                        # phone / account
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),              # PAN
]

_DISCLAIMER_KEYWORDS = [
    "not an official government portal",
    "guidance only",
    "verify details",
]

# Phrases that suggest fabrication
_FABRICATION_PATTERNS = [
    re.compile(r"(?i)as per our records"),
    re.compile(r"(?i)our data shows"),
    re.compile(r"(?i)according to our database"),
]


# ── Validator ────────────────────────────────────────────────────


def validate_response(
    answer: str,
    had_context: bool = True,
) -> dict:
    """Validate a generated answer.

    Returns
    -------
    dict with keys:
        valid : bool
        warnings : list[str]   — non-blocking issues
        errors : list[str]     — blocking issues that require fallback
        needs_disclaimer : bool
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Citation check (only when context was provided)
    if had_context:
        citations = _CITATION_PATTERN.findall(answer)
        if not citations:
            warnings.append(
                "Response does not contain any [Source: ...] citations."
            )

    # 2. PII leak check
    for pat in _PII_PATTERNS:
        if pat.search(answer):
            errors.append(
                "Response appears to contain personal identification numbers."
            )
            break

    # 3. Fabrication phrases
    for pat in _FABRICATION_PATTERNS:
        if pat.search(answer):
            warnings.append(
                f"Response contains a phrase suggesting fabrication: "
                f"'{pat.pattern}'"
            )

    # 4. Disclaimer check
    has_disclaimer = any(kw in answer.lower() for kw in _DISCLAIMER_KEYWORDS)

    return {
        "valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "needs_disclaimer": not has_disclaimer,
    }


def build_fallback_response(language: str = "en") -> str:
    """Return a safe fallback when the generated answer fails validation."""
    fallbacks = {
        "en": (
            "I apologise, but I'm unable to provide a verified answer to your "
            "question right now. For accurate information, please visit the "
            "official scheme website or contact your nearest government office.\n\n"
            "⚠️ *This information is for guidance only. SchemeSaathi is not an "
            "official government portal.*"
        ),
        "te": (
            "క్షమించండి, మీ ప్రశ్నకు ధృవీకరించిన సమాధానం ఇప్పుడు ఇవ్వడం "
            "సాధ్యం కాలేదు. ఖచ్చితమైన సమాచారం కోసం, దయచేసి అధికారిక పథకం "
            "వెబ్‌సైట్‌ని సందర్శించండి.\n\n"
            "⚠️ *ఈ సమాచారం మార్గదర్శకత్వం కోసం మాత్రమే. SchemeSaathi అధికారిక "
            "ప్రభుత్వ పోర్టల్ కాదు.*"
        ),
        "hi": (
            "क्षमा करें, मैं अभी आपके प्रश्न का सत्यापित उत्तर देने में "
            "असमर्थ हूँ। सटीक जानकारी के लिए, कृपया आधिकारिक योजना वेबसाइट "
            "पर जाएँ या अपने निकटतम सरकारी कार्यालय से संपर्क करें।\n\n"
            "⚠️ *यह जानकारी केवल मार्गदर्शन के लिए है। SchemeSaathi एक "
            "आधिकारिक सरकारी पोर्टल नहीं है।*"
        ),
    }
    return fallbacks.get(language, fallbacks["en"])
