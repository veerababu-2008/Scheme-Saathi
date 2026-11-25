"""SchemeSaathi AI — Text cleaning and normalisation for RAG ingestion.

Cleans raw text extracted from PDFs and HTML pages, removing noise
while preserving meaningful content structure.
"""

import re
import unicodedata


def normalise_unicode(text: str) -> str:
    """Apply NFC normalisation for consistent Indic script handling."""
    return unicodedata.normalize("NFC", text)


def collapse_whitespace(text: str) -> str:
    """Replace runs of whitespace (except newlines) with a single space."""
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_boilerplate(text: str) -> str:
    """Strip common government-document boilerplate noise."""
    patterns = [
        r"(?i)page\s*\d+\s*of\s*\d+",
        r"(?i)^\s*\d+\s*$",                       # bare page numbers
        r"(?i)confidential|draft|do not circulate",
        r"(?i)www\.\S+",                           # bare URLs (kept in metadata)
        r"(?i)^\s*[\-=_]{5,}\s*$",                 # horizontal rules
        r"(?i)copyright\s*©.*$",
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.MULTILINE)
    return text


def normalise_rupee(text: str) -> str:
    """Standardise rupee symbols: Rs., Rs, INR → ₹."""
    text = re.sub(r"\bRs\.?\s*", "₹", text)
    text = re.sub(r"\bINR\s*", "₹", text, flags=re.IGNORECASE)
    return text


def clean_text(text: str) -> str:
    """Full cleaning pipeline for a single document's text.

    Returns cleaned text ready for chunking.
    """
    if not text:
        return ""

    text = normalise_unicode(text)
    text = remove_boilerplate(text)
    text = normalise_rupee(text)
    text = collapse_whitespace(text)

    return text
