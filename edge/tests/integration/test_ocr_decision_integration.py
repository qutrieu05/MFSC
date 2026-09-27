"""P3.9: OCR integrates with msfc.decision.DecisionEngine WITHOUT any change to that package —
this is the actual point of the exercise, not just "OCR runs." DecisionEngine.decide() already
accepts any number of InspectionResult channels (docstring: "one per inspection channel...
OCR joins in Phase 3") and combines them with "any DEFECT wins" (fail-closed) — proven here by
combining a vision channel and an OCR channel for the same product.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from msfc.decision import DecisionEngine
from msfc.domain import InspectionResult, ModelInfo, RawVerdict, Verdict
from msfc.ocr.engine import MockOcrEngine
from msfc.ocr.models import OcrOutput
from msfc.ocr.pipeline import run_ocr_pipeline
from msfc.ocr.preprocess import PreprocessConfig
from msfc.ocr.validate import LabelValidationConfig

REF = date(2026, 1, 1)
LABEL_CONFIG = LabelValidationConfig(required_substrings=("PROD-A",))


def _vision_inspection(product_id: str, verdict: RawVerdict) -> InspectionResult:
    return InspectionResult(
        product_id=product_id, verdict=verdict, confidence=0.95,
        model=ModelInfo(name="vision-stub", version="1"), timings_ms={"total": 10.0},
    )


def _run_ocr(product_id: str, raw_text: str, confidence: float = 0.9) -> InspectionResult:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text=raw_text, confidence=confidence))
    return run_ocr_pipeline(
        np.zeros((60, 100, 3), dtype=np.uint8), engine=engine, preprocess_config=PreprocessConfig(),
        label_config=LABEL_CONFIG, reference_date=REF, product_id=product_id,
    )


def test_vision_good_and_ocr_good_combine_to_final_good() -> None:
    engine = DecisionEngine()
    vision = _vision_inspection("7-1", RawVerdict.GOOD)
    ocr = _run_ocr("7-1", "PROD-A EXP 01/06/2027")
    assert ocr.verdict is RawVerdict.GOOD

    record = engine.decide("7-1", [vision, ocr], detected_at_mono_ms=0, now_mono_ms=50)
    assert record.final_verdict is Verdict.GOOD
    assert "ALL_CHANNELS_GOOD" in record.reason_codes


def test_vision_good_but_ocr_expired_combine_to_final_defect() -> None:
    """The actual "why OCR matters" case: vision alone would pass this product, but the
    label says it's expired -- fail-closed, OCR's DEFECT must still win (FR-DEC-01)."""
    engine = DecisionEngine()
    vision = _vision_inspection("7-2", RawVerdict.GOOD)
    ocr = _run_ocr("7-2", "PROD-A EXP 01/06/2020")  # expired
    assert ocr.verdict is RawVerdict.DEFECT

    record = engine.decide("7-2", [vision, ocr], detected_at_mono_ms=0, now_mono_ms=50)
    assert record.final_verdict is Verdict.DEFECT
    assert any("DEFECT" in code for code in record.reason_codes)
    assert record.inputs[ocr.model.name]["verdict"] == "DEFECT"


def test_ocr_uncertain_resolves_per_the_existing_decision_policy() -> None:
    """Uses msfc.decision.DecisionPolicy exactly as it already exists (default: UNCERTAIN ->
    DEFECT, FR-DEC-04) -- no change to msfc.decision needed for OCR's UNCERTAIN to work."""
    engine = DecisionEngine()
    vision = _vision_inspection("7-3", RawVerdict.GOOD)
    ocr = _run_ocr("7-3", "", confidence=0.0)  # empty OCR read -> UNCERTAIN
    assert ocr.verdict is RawVerdict.UNCERTAIN

    record = engine.decide("7-3", [vision, ocr], detected_at_mono_ms=0, now_mono_ms=50)
    assert record.final_verdict is Verdict.DEFECT  # default policy resolves UNCERTAIN to DEFECT


def test_ocr_channel_alone_without_vision_also_works() -> None:
    """DecisionEngine.decide() requires at least one inspection, but doesn't require vision
    specifically -- OCR-only inspection (e.g. label station with no camera stage) is valid."""
    engine = DecisionEngine()
    ocr = _run_ocr("7-4", "PROD-A EXP 01/06/2027")
    record = engine.decide("7-4", [ocr], detected_at_mono_ms=0, now_mono_ms=10)
    assert record.final_verdict is Verdict.GOOD


def test_decision_engine_rejects_a_product_id_mismatch_between_channels() -> None:
    """Confirms DecisionEngine's existing validation (msfc/decision/engine.py) applies
    unchanged to an OCR-produced InspectionResult, same as a vision-produced one."""
    from msfc.core.errors import DecisionError

    engine = DecisionEngine()
    vision = _vision_inspection("7-5", RawVerdict.GOOD)
    ocr = _run_ocr("7-6", "PROD-A EXP 01/06/2027")  # different product_id
    with pytest.raises(DecisionError, match="does not match"):
        engine.decide("7-5", [vision, ocr], detected_at_mono_ms=0, now_mono_ms=10)
