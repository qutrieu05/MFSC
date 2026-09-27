"""OCR domain model (P3.1, FR-OCR).

Deliberately not coupled to any OCR engine: these are plain dataclasses any backend (mock,
deterministic-test, or a future real engine — Tesseract, PaddleOCR, a cloud API) can produce
and consume, mirroring how ``msfc.vision.inference.InferenceOutput`` is engine-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from msfc.core.errors import OcrError


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Pixel region an OCR engine reports text came from (image coordinates, x/y = top-left)."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise OcrError(f"BoundingBox width/height must be > 0, got {self.width}x{self.height}")
        if self.x < 0 or self.y < 0:
            raise OcrError(f"BoundingBox x/y must be >= 0, got ({self.x}, {self.y})")


@dataclass(frozen=True, slots=True)
class OcrOutput:
    """Raw output of one OCR engine call (P3.2) — before any normalization/extraction.

    ``raw_text`` is preserved unmodified for diagnostics (P3.4: "preserve raw OCR text") even
    after normalization produces a separate, cleaned string downstream.
    """

    raw_text: str
    confidence: float  # 0..1, engine's own confidence in raw_text
    bounding_box: BoundingBox | None = None
    timings_ms: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise OcrError(f"OcrOutput.confidence must be in [0, 1], got {self.confidence!r}")


class OcrReasonCode(str, Enum):
    """Exactly the 6 codes required by FR-OCR-04 (docs/REQUIREMENTS.md section 2.5) — no
    ad-hoc codes are added beyond this set; internal, finer-grained checks (P3.6/P3.7) all
    resolve to one of these six for the final result."""

    OK = "OK"
    EXPIRED = "EXPIRED"
    FORMAT_INVALID = "FORMAT_INVALID"
    UNREADABLE = "UNREADABLE"
    LABEL_MISSING = "LABEL_MISSING"
    LABEL_MISALIGNED = "LABEL_MISALIGNED"


@dataclass(frozen=True, slots=True)
class DateCandidate:
    """One date-shaped substring found in normalized text (P3.5), before/after correcting
    known OCR digit confusions (O/o->0, I/l/i->1, S/s->5, B->8) within that substring only."""

    raw_match: str
    corrected_text: str
    format_used: str | None  # one of msfc.ocr.text.SUPPORTED_DATE_FORMATS, or None if no format parsed it
    calendar_valid: bool
    date_iso: str | None  # 'YYYY-MM-DD', only when calendar_valid


@dataclass(frozen=True, slots=True)
class DateExtractionResult:
    """Result of scanning text for expiry-date-shaped substrings (P3.5)."""

    candidates: tuple[DateCandidate, ...] = ()

    @property
    def found(self) -> bool:
        return len(self.candidates) > 0

    @property
    def valid_candidates(self) -> tuple[DateCandidate, ...]:
        return tuple(c for c in self.candidates if c.calendar_valid)

    @property
    def ambiguous(self) -> bool:
        """True when more than one *distinct* calendar-valid date was found — extraction
        cannot determine which one is the real expiry (P3.6)."""
        distinct_dates = {c.date_iso for c in self.valid_candidates}
        return len(distinct_dates) > 1


@dataclass(frozen=True, slots=True)
class DetectedField:
    """One field the label-validation rules looked for and either found or didn't (P3.7)."""

    name: str
    found: bool
    value: str | None = None


@dataclass(frozen=True, slots=True)
class OcrValidationResult:
    """Everything P3.6/P3.7's checks produced for one label, before classification (P3.8).

    ``reason`` is always one of the 6 FR-OCR-04 codes. ``details`` carries the finer-grained
    facts (ambiguous match count, calendar-invalid flag, etc.) for diagnostics/tests without
    growing the FR-OCR-04 vocabulary itself.
    """

    reason: OcrReasonCode
    confidence: float
    fields: tuple[DetectedField, ...] = ()
    expiry_date_iso: str | None = None  # ISO 8601 'YYYY-MM-DD', only when a calendar-valid date was found
    ambiguous: bool = False  # True when multiple distinct valid dates were found (P3.6/P3.8) —
    # reason is still FORMAT_INVALID for diagnostics, but msfc.ocr.classify treats this as
    # UNCERTAIN rather than DEFECT (P3.8: "do not force uncertain OCR into GOOD/DEFECT")
    details: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise OcrError(f"OcrValidationResult.confidence must be in [0, 1], got {self.confidence!r}")
