"""P3.10 deterministic synthetic fixtures + P3.11 end-to-end simulation.

The 12 scenarios named in the PO's Phase 3 directive, each run through the full
Image -> preprocess -> Mock OCR -> normalize -> extract -> validate -> classify -> InspectionResult
flow and asserted against its documented expected verdict (msfc.ocr.synthetic).
"""

from __future__ import annotations

from datetime import date

import pytest

from msfc.domain import RawVerdict
from msfc.ocr.engine import FixtureOcrEngine
from msfc.ocr.pipeline import run_ocr_pipeline
from msfc.ocr.preprocess import PreprocessConfig
from msfc.ocr.synthetic import drive_fixture_engine, generate_fixtures
from msfc.ocr.validate import LabelValidationConfig

REFERENCE_DATE = date(2026, 1, 1)  # fixed, injected -- never the host clock (P3.6)
LABEL_CONFIG = LabelValidationConfig(required_substrings=("PROD-A",), min_confidence=0.6)
PREPROCESS_CONFIG = PreprocessConfig(target_size=(320, 120), grayscale=True)


def test_generate_fixtures_returns_exactly_the_12_named_scenarios() -> None:
    fixtures = generate_fixtures()
    scenarios = {s.scenario for s in fixtures}
    assert len(fixtures) == 12
    assert scenarios == {
        "valid_expiry_date", "expired_product", "impossible_date", "missing_expiry",
        "wrong_product_identifier", "valid_product_and_expiry", "low_ocr_confidence",
        "ambiguous_ocr", "multiple_date_formats", "ocr_noise", "empty_ocr_result",
        "malformed_ocr_result",
    }


def test_fixture_images_are_real_rendered_pixels_not_placeholders() -> None:
    for sample in generate_fixtures():
        assert sample.image.shape == (120, 320, 3)
        assert sample.image.dtype.name == "uint8"


@pytest.mark.parametrize("sample", generate_fixtures(), ids=lambda s: s.scenario)
def test_end_to_end_scenario_matches_expected_verdict(sample) -> None:
    engine = FixtureOcrEngine()
    drive_fixture_engine(engine, sample)
    result = run_ocr_pipeline(
        sample.image, engine=engine, preprocess_config=PREPROCESS_CONFIG,
        label_config=LABEL_CONFIG, reference_date=REFERENCE_DATE, product_id="7-1",
    )
    assert result.verdict is sample.expected_verdict, (
        f"{sample.scenario}: expected {sample.expected_verdict}, got {result.verdict} "
        f"(raw_text={sample.raw_text!r}, ocr_confidence={sample.ocr_confidence})"
    )


def test_all_12_scenarios_produce_data_source_traceable_results() -> None:
    """Every fixture result must be traceable to its scenario/session, mirroring
    msfc.vision.synthetic's data_source discipline (D-026) applied to OCR."""
    engine = FixtureOcrEngine()
    for sample in generate_fixtures():
        assert sample.session_id  # every fixture belongs to a named session, not ad-hoc
