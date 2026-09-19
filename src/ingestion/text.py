"""Text cleaning and stable ticket identity."""

import hashlib
import re
import unicodedata

_BR_TAG = re.compile(r"<\s*/?\s*br\s*/?\s*>", re.IGNORECASE)
# Some source rows contain the two characters backslash + n instead of a real newline.
# In this dataset they are always line breaks (no Windows paths or code appear in it).
_LITERAL_LINE_BREAK = re.compile(r"\\r\\n|\\n|\\r")
_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")
_BLANK_LINES = re.compile(r"\n{3,}")
_ANY_WHITESPACE = re.compile(r"\s+")


def clean_text(value: str | None) -> str | None:
    """Clean a free-text field for reading and later extraction.

    Converts <br> variants and literal "\\n" sequences to newlines, unescapes
    \\" to ", normalizes Unicode and whitespace, and keeps paragraph structure.
    Anonymization tokens such as <name> or <tel_num> are left untouched.
    Returns None when nothing is left.
    """
    if value is None:
        return None
    text = unicodedata.normalize("NFC", value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _LITERAL_LINE_BREAK.sub("\n", text)
    text = text.replace('\\"', '"')
    text = _BR_TAG.sub("\n", text)
    lines = [_HORIZONTAL_SPACE.sub(" ", line).strip() for line in text.split("\n")]
    text = _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()
    return text or None


def normalize_for_id(value: str | None) -> str:
    """Normalize a raw field for hashing: Unicode NFC, whitespace collapsed."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", value)
    return _ANY_WHITESPACE.sub(" ", text).strip()


def make_ticket_id(subject: str | None, body: str | None) -> str:
    """Stable ticket ID: SHA-256 of normalized subject + body.

    Computed from the raw text (not the cleaned text), so later changes to
    the cleaning rules never change existing IDs. Case is preserved.
    """
    payload = f"{normalize_for_id(subject)}\n{normalize_for_id(body)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
