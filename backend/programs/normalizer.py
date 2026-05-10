import re
import unicodedata

# Unicode Hebrew special punctuation
_GERSHAYIM = "״"  # ״  (Hebrew double geresh)
_GERESH = "׳"     # ׳  (Hebrew geresh)
# Directional marks to strip
_DIR_MARKS = frozenset("‎‏‪‫‬‭‮﻿")

# Institution slug → list of regex patterns that identify it in free text
_INSTITUTION_PATTERNS: dict[str, list[str]] = {
    "tau":      [r'ת["״]א', r"תל[- ]?אביב", r"\bTAU\b", r"tel[- ]?aviv"],
    "huji":     [r"עברית", r"ירושלים", r"\bHUJI\b", r"hebrew[- ]?u(?:niversity)?"],
    "technion": [r"טכניון", r"\btechnion\b"],
    "bgu":      [r'ב["״]ג', r"בן[- ]?גוריון", r"\bBGU\b", r"negev"],
    "biu":      [r"בר[- ]?אילן", r"\bBIU\b", r"bar[- ]?ilan"],
    "haifa":    [r"(?<!\w)חיפה", r"\bUH\b", r"(?:university[- ]?of[- ]?)?haifa"],
    "reichman": [r"רייכמן", r"\bIDC\b", r"herzliya", r"הרצליה"],
    "openu":    [r"הפתוחה", r"open[- ]?u(?:niversity)?"],
    "afeka":    [r"אפקה", r"\bafeka\b"],
}

_COMPILED: dict[str, list[re.Pattern]] = {
    slug: [re.compile(p, re.IGNORECASE | re.UNICODE) for p in pats]
    for slug, pats in _INSTITUTION_PATTERNS.items()
}


def normalize_text(text: str) -> str:
    """
    Canonical form for matching.
    - Strips RTL/LTR marks and Hebrew nikud
    - Converts gershayim/geresh to ASCII equivalents
    - Lowercases ASCII, preserves Hebrew
    - Collapses whitespace
    """
    if not text:
        return ""
    # Drop directional marks
    text = "".join(c for c in text if c not in _DIR_MARKS)
    # Hebrew punctuation → ASCII equivalents so ״ == " and ׳ == '
    text = text.replace(_GERSHAYIM, '"').replace(_GERESH, "'")
    # Strip nikud (U+05B0–U+05C7)
    text = "".join(c for c in text if not ("ְ" <= c <= "ׇ"))
    # NFC
    text = unicodedata.normalize("NFC", text)
    # Lowercase ASCII only
    text = re.sub(r"[a-zA-Z]+", lambda m: m.group().lower(), text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip()


def detect_institution_slug(text: str) -> str | None:
    """Return the first institution slug found in `text`, or None."""
    for slug, patterns in _COMPILED.items():
        for pat in patterns:
            if pat.search(text):
                return slug
    return None


def strip_institution_refs(text: str) -> str:
    """Remove institution name mentions so only the program part remains."""
    result = text
    for patterns in _COMPILED.values():
        for pat in patterns:
            result = pat.sub(" ", result)
    return re.sub(r"\s+", " ", result).strip()
