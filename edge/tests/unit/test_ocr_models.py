"""P3.1: OCR domain model."""

from __future__ import annotations

import pytest

from msfc.core.errors import OcrError
from msfc.ocr.models import (
    BoundingBox,
    DateCandidate,
    DateExtractionResult,
    DetectedField,
    OcrOutput,
    OcrReasonCode,
    OcrValidationResult,
)


def test_bounding_box_rejects_non_positive_dimensions() -> None:
    with pytest.raises(OcrError, match="width/height"):
        BoundingBox(x=0, y=0, width=0, height=10)
    with pytest.raises(OcrError, match="width/height"):
        BoundingBox(x=0, y=0, width=10, height=-1)


def test_bounding_box_rejects_negative_origin() -> None:
    with pytest.raises(OcrError, match="x/y"):
        BoundingBox(x=-1, y=0, width=10, height=10)


def test_ocr_output_confidence_must_be_unit_interval() -> None:
    OcrOutput(raw_text="x", confidence=0.0)
    OcrOutput(raw_text="x", confidence=1.0)
    with pytest.raises(OcrError, match="confidence"):
        OcrOutput(raw_text="x", confidence=1.5)
    with pytest.raises(OcrError, match="confidence"):
        OcrOutput(raw_text="x", confidence=-0.1)


def test_ocr_reason_code_is_exactly_the_six_fr_ocr_04_codes() -> None:
    assert {c.value for c in OcrReasonCode} == {
        "OK", "EXPIRED", "FORMAT_INVALID", "UNREADABLE", "LABEL_MISSING", "LABEL_MISALIGNED",
    }


def test_date_extraction_result_found_reflects_candidates() -> None:
    empty = DateExtractionResult()
    assert not empty.found
    assert not empty.ambiguous
    assert empty.valid_candidates == ()

    one = DateExtractionResult(candidates=(
        DateCandidate(raw_match="01/06/2027", corrected_text="01/06/2027",
                       format_used="DD/MM/YYYY", calendar_valid=True, date_iso="2027-06-01"),
    ))
    assert one.found
    assert not one.ambiguous
    assert len(one.valid_candidates) == 1


def test_date_extraction_result_ambiguous_only_for_distinct_valid_dates() -> None:
    same_date_twice = DateExtractionResult(candidates=(
        DateCandidate("01/06/2027", "01/06/2027", "DD/MM/YYYY", True, "2027-06-01"),
        DateCandidate("01/06/2027", "01/06/2027", "DD/MM/YYYY", True, "2027-06-01"),
    ))
    assert not same_date_twice.ambiguous  # identical dates, not actually ambiguous

    two_distinct = DateExtractionResult(candidates=(
        DateCandidate("01/06/2027", "01/06/2027", "DD/MM/YYYY", True, "2027-06-01"),
        DateCandidate("02/07/2027", "02/07/2027", "DD/MM/YYYY", True, "2027-07-02"),
    ))
    assert two_distinct.ambiguous

    one_valid_one_invalid = DateExtractionResult(candidates=(
        DateCandidate("01/06/2027", "01/06/2027", "DD/MM/YYYY", True, "2027-06-01"),
        DateCandidate("31/02/2027", "31/02/2027", None, False, None),
    ))
    assert not one_valid_one_invalid.ambiguous  # only one calendar-valid candidate


def test_detected_field() -> None:
    found = DetectedField(name="product_id", found=True, value="PROD-A")
    missing = DetectedField(name="product_id", found=False)
    assert found.found and found.value == "PROD-A"
    assert not missing.found and missing.value is None


def test_ocr_validation_result_confidence_must_be_unit_interval() -> None:
    OcrValidationResult(reason=OcrReasonCode.OK, confidence=0.5)
    with pytest.raises(OcrError, match="confidence"):
        OcrValidationResult(reason=OcrReasonCode.OK, confidence=2.0)
