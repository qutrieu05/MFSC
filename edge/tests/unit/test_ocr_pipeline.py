"""P3.9 end-to-end flow (single-stage focus) + P3.12 error handling."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from msfc.core.errors import OcrError
from msfc.domain import RawVerdict
from msfc.ocr.engine import MockOcrEngine
from msfc.ocr.models import OcrOutput
from msfc.ocr.pipeline import run_ocr_pipeline
from msfc.ocr.preprocess import PreprocessConfig, RoiConfig
from msfc.ocr.validate import LabelValidationConfig

REF = date(2026, 1, 1)


def _image(width: int = 100, height: int = 60) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def test_pipeline_happy_path_produces_good() -> None:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text="PROD-A EXP 01/06/2027", confidence=0.9))
    result = run_ocr_pipeline(
        _image(), engine=engine, preprocess_config=PreprocessConfig(),
        label_config=LabelValidationConfig(required_substrings=("PROD-A",)),
        reference_date=REF, product_id="7-1",
    )
    assert result.verdict is RawVerdict.GOOD
    assert result.model.name == engine.name
    assert result.model.backend == "ocr"


def test_pipeline_records_timings_for_every_stage() -> None:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text="PROD-A EXP 01/06/2027", confidence=0.9))
    result = run_ocr_pipeline(
        _image(), engine=engine, preprocess_config=PreprocessConfig(),
        label_config=LabelValidationConfig(required_substrings=("PROD-A",)),
        reference_date=REF, product_id="7-1",
    )
    for stage in ("preprocess", "ocr", "normalize", "validate_and_extract", "total"):
        assert stage in result.timings_ms
        assert result.timings_ms[stage] >= 0


# --------------------------------------------------------------------------- P3.12 error handling
def test_pipeline_handles_an_ocr_engine_that_raises() -> None:
    class BrokenEngine:
        name = "broken"
        version = "0"

        def read(self, image: np.ndarray) -> OcrOutput:
            raise RuntimeError("engine unavailable")

    result = run_ocr_pipeline(
        _image(), engine=BrokenEngine(), preprocess_config=PreprocessConfig(),
        label_config=LabelValidationConfig(), reference_date=REF, product_id="7-1",
    )
    assert result.verdict is RawVerdict.UNCERTAIN  # UNREADABLE -> UNCERTAIN, not a crash


def test_pipeline_propagates_a_preprocessing_configuration_error() -> None:
    """A misconfigured ROI (caller bug, not OCR content) should surface, not be silently
    swallowed into a fake result — P3.12 distinguishes pipeline bugs from content problems."""
    engine = MockOcrEngine()
    bad_config = PreprocessConfig(roi=RoiConfig(x=0, y=0, width=9999, height=9999))
    with pytest.raises(OcrError, match="exceeds image bounds"):
        run_ocr_pipeline(_image(), engine=engine, preprocess_config=bad_config,
                          label_config=LabelValidationConfig(), reference_date=REF, product_id="7-1")


def test_pipeline_handles_empty_ocr_output_deterministically() -> None:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text="", confidence=0.0))
    result = run_ocr_pipeline(
        _image(), engine=engine, preprocess_config=PreprocessConfig(),
        label_config=LabelValidationConfig(required_substrings=("PROD-A",)),
        reference_date=REF, product_id="7-1",
    )
    assert result.verdict is RawVerdict.UNCERTAIN


def test_pipeline_handles_unsupported_date_format_deterministically() -> None:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text="PROD-A EXP 2027.06.01", confidence=0.9))
    result = run_ocr_pipeline(
        _image(), engine=engine, preprocess_config=PreprocessConfig(),
        label_config=LabelValidationConfig(required_substrings=("PROD-A",)),
        reference_date=REF, product_id="7-1",
    )
    assert result.verdict is RawVerdict.DEFECT  # date present but in an unsupported/unmatched shape


def test_pipeline_is_deterministic_across_repeated_runs() -> None:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text="PROD-A EXP 01/06/2027", confidence=0.9))
    config = PreprocessConfig()
    label_config = LabelValidationConfig(required_substrings=("PROD-A",))
    results = [
        run_ocr_pipeline(_image(), engine=engine, preprocess_config=config,
                          label_config=label_config, reference_date=REF, product_id="7-1")
        for _ in range(3)
    ]
    assert len({r.verdict for r in results}) == 1
