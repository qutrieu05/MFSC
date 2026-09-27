"""P3.8 result classification + P3.9's InspectionResult wrapping."""

from __future__ import annotations

from msfc.domain import ModelInfo, RawVerdict
from msfc.ocr.classify import classify, to_inspection_result
from msfc.ocr.models import OcrReasonCode, OcrValidationResult

MODEL = ModelInfo(name="test-ocr", version="1")


def test_ok_with_sufficient_confidence_is_good() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.OK, confidence=0.9)
    assert classify(result, min_confidence=0.6) is RawVerdict.GOOD


def test_expired_with_sufficient_confidence_is_defect() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.EXPIRED, confidence=0.9)
    assert classify(result, min_confidence=0.6) is RawVerdict.DEFECT


def test_format_invalid_is_defect() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.FORMAT_INVALID, confidence=0.9)
    assert classify(result, min_confidence=0.6) is RawVerdict.DEFECT


def test_label_missing_is_defect() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.LABEL_MISSING, confidence=0.9)
    assert classify(result, min_confidence=0.6) is RawVerdict.DEFECT


def test_label_misaligned_is_defect() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.LABEL_MISALIGNED, confidence=0.9)
    assert classify(result, min_confidence=0.6) is RawVerdict.DEFECT


def test_unreadable_is_always_uncertain_even_with_high_confidence() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.UNREADABLE, confidence=0.99)
    assert classify(result, min_confidence=0.6) is RawVerdict.UNCERTAIN


def test_low_confidence_forces_uncertain_regardless_of_reason() -> None:
    good_reason_low_confidence = OcrValidationResult(reason=OcrReasonCode.OK, confidence=0.2)
    assert classify(good_reason_low_confidence, min_confidence=0.6) is RawVerdict.UNCERTAIN

    defect_reason_low_confidence = OcrValidationResult(reason=OcrReasonCode.EXPIRED, confidence=0.2)
    assert classify(defect_reason_low_confidence, min_confidence=0.6) is RawVerdict.UNCERTAIN


def test_ambiguous_is_uncertain_never_defect_even_with_high_confidence() -> None:
    """P3.8: 'do not force uncertain OCR into GOOD/DEFECT' -- ambiguous overrides a
    reason (FORMAT_INVALID) that would otherwise mean DEFECT."""
    result = OcrValidationResult(reason=OcrReasonCode.FORMAT_INVALID, confidence=0.95, ambiguous=True)
    assert classify(result, min_confidence=0.6) is RawVerdict.UNCERTAIN


def test_confidence_exactly_at_threshold_is_not_uncertain() -> None:
    result = OcrValidationResult(reason=OcrReasonCode.OK, confidence=0.6)
    assert classify(result, min_confidence=0.6) is RawVerdict.GOOD


def test_to_inspection_result_produces_a_valid_domain_object() -> None:
    validation = OcrValidationResult(reason=OcrReasonCode.OK, confidence=0.9)
    inspection = to_inspection_result(
        validation, RawVerdict.GOOD, product_id="7-1", model=MODEL,
        timings_ms={"preprocess": 1.0, "ocr": 2.0}, frame_seq=5,
    )
    assert inspection.product_id == "7-1"
    assert inspection.verdict is RawVerdict.GOOD
    assert inspection.confidence == 0.9
    assert inspection.model is MODEL
    assert inspection.timings_ms["total"] == 3.0
    assert inspection.class_scores == {}
    assert inspection.frame_seq == 5


def test_to_inspection_result_respects_an_explicit_total_timing() -> None:
    validation = OcrValidationResult(reason=OcrReasonCode.OK, confidence=0.9)
    inspection = to_inspection_result(
        validation, RawVerdict.GOOD, product_id="7-1", model=MODEL,
        timings_ms={"total": 99.0, "ocr": 2.0},
    )
    assert inspection.timings_ms["total"] == 99.0
