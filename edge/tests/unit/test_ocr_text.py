"""P3.4 text normalization + P3.5 date extraction."""

from __future__ import annotations

from msfc.ocr.text import SUPPORTED_DATE_FORMATS, extract_dates, normalize_case, normalize_text, normalize_whitespace


def test_supported_date_formats_are_exactly_the_five_po_named() -> None:
    assert SUPPORTED_DATE_FORMATS == ("DD/MM/YYYY", "DD-MM-YYYY", "YYYY/MM/DD", "YYYY-MM-DD", "MM/YYYY")


def test_normalize_whitespace_collapses_and_strips() -> None:
    assert normalize_whitespace("  PROD-A   EXP\t01/06/2027 \n") == "PROD-A EXP 01/06/2027"


def test_normalize_case_uppercases() -> None:
    assert normalize_case("prod-a exp") == "PROD-A EXP"


def test_normalize_text_composes_both() -> None:
    assert normalize_text("  prod-a   exp 01/06/2027 ") == "PROD-A EXP 01/06/2027"


def test_normalize_text_never_raises_on_empty_string() -> None:
    assert normalize_text("") == ""


# --------------------------------------------------------------------------- date extraction
def test_extract_dates_finds_nothing_in_plain_text() -> None:
    result = extract_dates("PROD-A NO DATE HERE")
    assert not result.found


def test_extract_dates_dd_mm_yyyy() -> None:
    result = extract_dates("EXP 01/06/2027")
    assert result.found
    assert result.valid_candidates[0].date_iso == "2027-06-01"
    assert result.valid_candidates[0].format_used == "DD/MM/YYYY"


def test_extract_dates_dd_mm_yyyy_dash() -> None:
    result = extract_dates("EXP 01-06-2027")
    assert result.valid_candidates[0].date_iso == "2027-06-01"
    assert result.valid_candidates[0].format_used == "DD-MM-YYYY"


def test_extract_dates_yyyy_mm_dd_slash() -> None:
    result = extract_dates("EXP 2027/06/01")
    assert result.valid_candidates[0].date_iso == "2027-06-01"
    assert result.valid_candidates[0].format_used == "YYYY/MM/DD"


def test_extract_dates_yyyy_mm_dd_dash() -> None:
    result = extract_dates("EXP 2027-06-01")
    assert result.valid_candidates[0].date_iso == "2027-06-01"
    assert result.valid_candidates[0].format_used == "YYYY-MM-DD"


def test_extract_dates_mm_yyyy() -> None:
    result = extract_dates("EXP 06/2027")
    assert result.valid_candidates[0].date_iso == "2027-06-01"
    assert result.valid_candidates[0].format_used == "MM/YYYY"


def test_extract_dates_rejects_calendar_invalid_date() -> None:
    result = extract_dates("EXP 31/02/2027")
    assert result.found  # date-shaped text was there
    assert not result.valid_candidates  # but no format made it a real calendar date


def test_extract_dates_corrects_deterministic_digit_confusions() -> None:
    result = extract_dates("EXP O1/O6/2O27")  # 'O' for '0'
    assert result.valid_candidates[0].date_iso == "2027-06-01"
    assert result.valid_candidates[0].raw_match == "O1/O6/2O27"  # raw preserved
    assert result.valid_candidates[0].corrected_text == "01/06/2027"


def test_extract_dates_does_not_correct_non_date_shaped_text() -> None:
    """P3.4: normalization/correction must not silently invent a date from arbitrary text."""
    result = extract_dates("SOLD BY STORE")  # contains letters this map would touch (S, B) but no '/'/'-' shape
    assert not result.found


def test_extract_dates_flags_two_distinct_valid_dates_as_ambiguous() -> None:
    result = extract_dates("EXP 01/06/2027 OR 02/07/2027")
    assert result.ambiguous


def test_extract_dates_does_not_flag_the_same_date_repeated_as_ambiguous() -> None:
    result = extract_dates("EXP 01/06/2027 SEE ALSO 01/06/2027")
    assert not result.ambiguous


def test_extract_dates_tries_formats_in_the_documented_order() -> None:
    """DD/MM/YYYY is tried before YYYY/MM/DD -- '01/06/2027' must resolve as 1 June, not be
    misread by a later-tried format (there's no valid YYYY/MM/DD reading of this string anyway,
    but this pins the documented try-order contract for future format additions)."""
    result = extract_dates("01/06/2027")
    assert result.valid_candidates[0].format_used == SUPPORTED_DATE_FORMATS[0]
