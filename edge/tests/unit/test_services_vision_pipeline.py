"""P6.2: vision-channel composition tests."""

from __future__ import annotations

import numpy as np
import pytest

from msfc.core.errors import VisionError
from msfc.domain import ModelInfo, RawVerdict
from msfc.services.vision_pipeline import run_vision_pipeline
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

ROI = RoiConfig(x=0, y=0, width=32, height=32, target_size=(32, 32))
MODEL = ModelInfo(name="stub", version="1")
THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)


class _StubEngine:
    name = "stub"
    version = "1"

    def __init__(self, defect_score: float) -> None:
        self._defect_score = defect_score

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 1 - self._defect_score, "DEFECT": self._defect_score},
                                timings_ms={"inference": 0.1})


class _CrashingEngine:
    name = "crashing"
    version = "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        raise RuntimeError("model backend crashed")


def _frame(size: int = 32) -> Frame:
    image = np.zeros((size, size, 3), dtype=np.uint8)
    return Frame(image=image, seq=0, captured_mono_ms=0, source="test")


def test_run_vision_pipeline_returns_good() -> None:
    result = run_vision_pipeline(_frame(), engine=_StubEngine(0.02), roi=ROI, thresholds=THRESHOLDS,
                                  model=MODEL, product_id="1-0")
    assert result.verdict is RawVerdict.GOOD
    assert result.product_id == "1-0"


def test_run_vision_pipeline_returns_defect() -> None:
    result = run_vision_pipeline(_frame(), engine=_StubEngine(0.98), roi=ROI, thresholds=THRESHOLDS,
                                  model=MODEL, product_id="1-0")
    assert result.verdict is RawVerdict.DEFECT


def test_run_vision_pipeline_returns_uncertain_in_the_threshold_band() -> None:
    result = run_vision_pipeline(_frame(), engine=_StubEngine(0.5), roi=ROI, thresholds=THRESHOLDS,
                                  model=MODEL, product_id="1-0")
    assert result.verdict is RawVerdict.UNCERTAIN


def test_run_vision_pipeline_raises_when_roi_does_not_fit() -> None:
    tiny_frame = _frame(size=8)  # smaller than ROI's 32x32
    with pytest.raises(VisionError):
        run_vision_pipeline(tiny_frame, engine=_StubEngine(0.02), roi=ROI, thresholds=THRESHOLDS,
                             model=MODEL, product_id="1-0")


def test_run_vision_pipeline_propagates_engine_crash() -> None:
    with pytest.raises(RuntimeError):
        run_vision_pipeline(_frame(), engine=_CrashingEngine(), roi=ROI, thresholds=THRESHOLDS,
                             model=MODEL, product_id="1-0")
