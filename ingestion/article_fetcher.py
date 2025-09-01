
"""Helpers for fetching/cleaning article text used by tests."""
import re

_WS = re.compile(r"\s+", re.MULTILINE)
_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def clean_text(text: str) -> str:
    """Return a normalized text string suitable for ingestion.
    - Replace non-breaking spaces with normal spaces
    - Drop ASCII control characters
    - Collapse all consecutive whitespace to a single space
    - Strip leading/trailing whitespace
    """
    if text is None:
        return ""
    s = str(text).replace("\xa0", " ")
    s = _CTRL.sub("", s)
    s = _WS.sub(" ", s)
    return s.strip()
