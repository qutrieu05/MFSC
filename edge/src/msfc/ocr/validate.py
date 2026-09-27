"""Date validation (P3.6) and label/product validation (P3.7).

Produces an :class:`~msfc.ocr.models.OcrValidationResult` whose ``reason`` is always one of
the 6 FR-OCR-04 codes (msfc.ocr.models.OcrReasonCode) — every finer-grained condition below
(missing expiry, ambiguous expiry, impossible/calendar-invalid date, wrong product id) resolves
to one of those six; see the mapping table in each branch's comment and D-042 (DECISIONS.md)
for why no extra codes were added.

OCR-confidence thresholding is deliberately NOT done here (see msfc.ocr.classify) — a
low-confidence read should become UNCERTAIN, not silently reported as a definite DEFECT
reason like FORMAT_INVALID (P3.8: "do not force uncertain OCR into GOOD/DEFECT").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from msfc.core.errors import OcrError
from msfc.ocr.models import DateExtractionResult, DetectedField, OcrReasonCode, OcrValidationResult
from msfc.ocr.text import extract_dates


@dataclass(frozen=True, slots=True)
class LabelValidationConfig:
    """Configurable label rules (P3.7) — never references one specific real product."""

    required_substrings: tuple[str, ...] = ()
    expected_product_id_pattern: str | None = None  # regex matched against normalized text
    max_skew_deg: float = 5.0  # beyond this, the label is reported misaligned, not misread
    min_confidence: float = 0.6  # P3.7's "OCR confidence threshold" — applied by msfc.ocr.classify

    def __post_init__(self) -> None:
        if self.expected_product_id_pattern is not None:
            try:
                re.compile(self.expected_product_id_pattern)
            except re.error as exc:
                raise OcrError(f"expected_product_id_pattern is not a valid regex: {exc}") from exc
        if not (0.0 <= self.min_confidence <= 1.0):
            raise OcrError(f"min_confidence must be in [0, 1], got {self.min_confidence!r}")


def _check_required_fields(normalized_text: str, config: LabelValidationConfig) -> tuple[DetectedField, ...]:
    fields = []
    for substring in config.required_substrings:
        fields.append(DetectedField(name=substring, found=substring in normalized_text))
    if config.expected_product_id_pattern is not None:
        match = re.search(config.expected_product_id_pattern, normalized_text)
        fields.append(DetectedField(
            name="product_id", found=match is not None, value=match.group(0) if match else None
        ))
    return tuple(fields)


def validate_label(
    normalized_text: str,
    ocr_confidence: float,
    *,
    config: LabelValidationConfig,
    reference_date: date,
    skew_deg: float = 0.0,
) -> OcrValidationResult:
    """*normalized_text* must already be normalized (msfc.ocr.text.normalize_text)."""
    if not normalized_text.strip():
        return OcrValidationResult(reason=OcrReasonCode.UNREADABLE, confidence=ocr_confidence,
                                    details={"cause": "empty normalized text"})

    if abs(skew_deg) > config.max_skew_deg:
        return OcrValidationResult(reason=OcrReasonCode.LABEL_MISALIGNED, confidence=ocr_confidence,
                                    details={"skew_deg": skew_deg, "max_skew_deg": config.max_skew_deg})

    fields = _check_required_fields(normalized_text, config)
    missing = [f.name for f in fields if not f.found]
    if missing:
        return OcrValidationResult(reason=OcrReasonCode.LABEL_MISSING, confidence=ocr_confidence,
                                    fields=fields, details={"missing_fields": missing})

    extraction: DateExtractionResult = extract_dates(normalized_text)

    if not extraction.found:
        return OcrValidationResult(reason=OcrReasonCode.FORMAT_INVALID, confidence=ocr_confidence,
                                    fields=fields, details={"cause": "no expiry date found"})

    if extraction.ambiguous:
        return OcrValidationResult(
            reason=OcrReasonCode.FORMAT_INVALID, confidence=ocr_confidence, fields=fields,
            ambiguous=True,
            details={"cause": "ambiguous expiry", "candidates": [c.raw_match for c in extraction.valid_candidates]},
        )

    if not extraction.valid_candidates:
        # Date-shaped text was found but none of it is a real calendar date, or none matched
        # a supported format (P3.5: "do not assume formats that are not explicitly supported").
        return OcrValidationResult(
            reason=OcrReasonCode.FORMAT_INVALID, confidence=ocr_confidence, fields=fields,
            details={"cause": "no calendar-valid date in a supported format",
                     "raw_candidates": [c.raw_match for c in extraction.candidates]},
        )

    winner = extraction.valid_candidates[0]
    expiry = date.fromisoformat(winner.date_iso)  # type: ignore[arg-type]
    if expiry < reference_date:
        return OcrValidationResult(reason=OcrReasonCode.EXPIRED, confidence=ocr_confidence,
                                    fields=fields, expiry_date_iso=winner.date_iso,
                                    details={"reference_date": reference_date.isoformat()})

    return OcrValidationResult(reason=OcrReasonCode.OK, confidence=ocr_confidence, fields=fields,
                                expiry_date_iso=winner.date_iso)
