"""P3.6 date validation + P3.7 label/product validation."""

from __future__ import annotations

from datetime import date

import pytest

from msfc.core.errors import OcrError
from msfc.ocr.models import OcrReasonCode
from msfc.ocr.text import normalize_text
from msfc.ocr.validate import LabelValidationConfig, validate_label

REF = date(2026, 1, 1)
CONFIG = LabelValidationConfig(required_substrings=("PROD-A",), min_confidence=0.6)


def _validate(raw_text: str, confidence: float = 0.9, *, config: LabelValidationConfig = CONFIG,
              skew_deg: float = 0.0, reference_date: date = REF):
    return validate_label(normalize_text(raw_text), confidence, config=config,
                           reference_date=reference_date, skew_deg=skew_deg)


def test_label_validation_config_rejects_invalid_regex() -> None:
    with pytest.raises(OcrError, match="regex"):
        LabelValidationConfig(expected_product_id_pattern="[")


def test_label_validation_config_rejects_out_of_range_min_confidence() -> None:
    with pytest.raises(OcrError, match="min_confidence"):
        LabelValidationConfig(min_confidence=1.5)


def test_empty_text_is_unreadable() -> None:
    result = _validate("")
    assert result.reason is OcrReasonCode.UNREADABLE


def test_whitespace_only_text_is_unreadable() -> None:
    result = _validate("   \n\t  ")
    assert result.reason is OcrReasonCode.UNREADABLE


def test_skew_beyond_threshold_is_misaligned_even_with_otherwise_valid_text() -> None:
    """Skew is checked before the required-field/date checks: a severely tilted label is
    reported as misaligned rather than (misleadingly) missing or expired."""
    result = _validate("PROD-A EXP 01/06/2027", skew_deg=10.0,
                        config=LabelValidationConfig(required_substrings=("PROD-A",), max_skew_deg=5.0))
    assert result.reason is OcrReasonCode.LABEL_MISALIGNED


def test_skew_within_threshold_does_not_trigger_misaligned() -> None:
    result = _validate("PROD-A EXP 01/06/2027", skew_deg=3.0,
                        config=LabelValidationConfig(required_substrings=("PROD-A",), max_skew_deg=5.0))
    assert result.reason is OcrReasonCode.OK


def test_missing_required_substring_is_label_missing() -> None:
    result = _validate("PROD-Z EXP 01/06/2027")
    assert result.reason is OcrReasonCode.LABEL_MISSING
    assert result.fields[0].name == "PROD-A" and not result.fields[0].found


def test_missing_product_id_pattern_is_label_missing() -> None:
    config = LabelValidationConfig(expected_product_id_pattern=r"PROD-\d+")
    result = _validate("PROD-A EXP 01/06/2027", config=config)
    assert result.reason is OcrReasonCode.LABEL_MISSING


def test_matching_product_id_pattern_records_the_matched_value() -> None:
    config = LabelValidationConfig(expected_product_id_pattern=r"PROD-\d+")
    result = _validate("PROD-42 EXP 01/06/2027", config=config)
    assert result.reason is OcrReasonCode.OK
    product_field = next(f for f in result.fields if f.name == "product_id")
    assert product_field.found and product_field.value == "PROD-42"


def test_no_date_found_is_format_invalid() -> None:
    result = _validate("PROD-A NO DATE HERE")
    assert result.reason is OcrReasonCode.FORMAT_INVALID
    assert not result.ambiguous


def test_calendar_invalid_date_is_format_invalid() -> None:
    result = _validate("PROD-A EXP 31/02/2027")
    assert result.reason is OcrReasonCode.FORMAT_INVALID


def test_ambiguous_dates_are_format_invalid_and_flagged_ambiguous() -> None:
    result = _validate("PROD-A EXP 01/06/2027 OR 02/07/2027")
    assert result.reason is OcrReasonCode.FORMAT_INVALID
    assert result.ambiguous


def test_past_date_is_expired() -> None:
    result = _validate("PROD-A EXP 01/06/2020")
    assert result.reason is OcrReasonCode.EXPIRED
    assert result.expiry_date_iso == "2020-06-01"


def test_future_date_is_ok() -> None:
    result = _validate("PROD-A EXP 01/06/2027")
    assert result.reason is OcrReasonCode.OK
    assert result.expiry_date_iso == "2027-06-01"


def test_expiry_exactly_on_reference_date_is_ok_not_expired() -> None:
    result = _validate("PROD-A EXP 01/01/2026", reference_date=date(2026, 1, 1))
    assert result.reason is OcrReasonCode.OK


def test_confidence_is_passed_through_unchanged() -> None:
    result = _validate("PROD-A EXP 01/06/2027", confidence=0.37)
    assert result.confidence == 0.37


def test_no_required_fields_configured_skips_label_missing_check() -> None:
    result = _validate("EXP 01/06/2027", config=LabelValidationConfig())
    assert result.reason is OcrReasonCode.OK
