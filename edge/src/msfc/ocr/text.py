"""Text normalization (P3.4) and expiry-date extraction (P3.5).

P3.4 rule, followed strictly: only *unambiguous* cleanup runs on the whole text
(``normalize_text``: whitespace, case). Character-confusion correction (P3.5's "OCR confusion
handling where deterministic and justified") is scoped to substrings that already look
date-shaped — never applied blindly across arbitrary text, so a garbled label is never
silently turned into a fabricated valid date (P3.4: "do not silently correct uncertain text
into a valid date"). ``raw_text`` (msfc.ocr.models.OcrOutput) is never mutated; normalization
always produces a *new* string, kept alongside the original for diagnostics.
"""

from __future__ import annotations

import re
from datetime import date

from msfc.ocr.models import DateCandidate, DateExtractionResult

# Exactly the formats P3.5 names — extraction never assumes a format outside this set.
SUPPORTED_DATE_FORMATS: tuple[str, ...] = (
    "DD/MM/YYYY", "DD-MM-YYYY", "YYYY/MM/DD", "YYYY-MM-DD", "MM/YYYY",
)

_STRPTIME_BY_FORMAT: dict[str, str] = {
    "DD/MM/YYYY": "%d/%m/%Y",
    "DD-MM-YYYY": "%d-%m-%Y",
    "YYYY/MM/DD": "%Y/%m/%d",
    "YYYY-MM-DD": "%Y-%m-%d",
    "MM/YYYY": "%m/%Y",
}

# A date-shaped token: 2 or 3 digit-or-confusable groups separated by '/' or '-', each 1-4
# characters (covers DD/MM/YYYY's 2-2-4 down to MM/YYYY's 2-4). Deliberately permissive on
# digit-vs-confusable-letter and on group length -- exact validity is strptime's job below,
# via _STRPTIME_BY_FORMAT; this regex only decides "shaped enough to be worth trying."
_DATE_CANDIDATE_RE = re.compile(
    r"\b[0-9OoIlSsBb]{1,4}[/\-][0-9OoIlSsBb]{1,4}(?:[/\-][0-9OoIlSsBb]{1,4})?\b"
)

# Classic OCR digit confusions — applied ONLY within an already date-shaped candidate span.
_DIGIT_CONFUSIONS = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "i": "1",
                                    "S": "5", "s": "5", "B": "8"})


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_case(text: str) -> str:
    return text.upper()


def normalize_text(text: str) -> str:
    """The one normalization every downstream stage should read from — whitespace-collapsed,
    uppercased. Never mutates or discards the caller's original ``raw_text``."""
    return normalize_case(normalize_whitespace(text))


def _correct_digit_confusions(candidate: str) -> str:
    return candidate.translate(_DIGIT_CONFUSIONS)


def _parse_candidate(raw_match: str) -> DateCandidate:
    corrected = _correct_digit_confusions(raw_match)
    for fmt in SUPPORTED_DATE_FORMATS:
        try:
            parsed = date_from_strptime(corrected, _STRPTIME_BY_FORMAT[fmt])
        except ValueError:
            continue
        return DateCandidate(raw_match=raw_match, corrected_text=corrected, format_used=fmt,
                              calendar_valid=True, date_iso=parsed.isoformat())
    return DateCandidate(raw_match=raw_match, corrected_text=corrected, format_used=None,
                          calendar_valid=False, date_iso=None)


def date_from_strptime(text: str, fmt: str) -> date:
    """Thin wrapper so both calendar-validity (real Python `datetime` rules, e.g. rejects
    2024-02-30) and format-matching happen in one call, matching strptime's own behavior."""
    from datetime import datetime

    return datetime.strptime(text, fmt).date()


def extract_dates(normalized_text: str) -> DateExtractionResult:
    """Scan *normalized_text* (already run through :func:`normalize_text`) for expiry-date-
    shaped substrings and attempt to parse each against every supported format in order."""
    matches = _DATE_CANDIDATE_RE.findall(normalized_text)
    candidates = tuple(_parse_candidate(m) for m in matches)
    return DateExtractionResult(candidates=candidates)
