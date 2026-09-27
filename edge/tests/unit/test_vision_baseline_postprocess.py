"""Tests for msfc.vision.baseline.ClassicCvBaseline and msfc.vision.postprocess."""

from __future__ import annotations

import numpy as np
import pytest

from msfc.core.errors import DomainError, VisionError
from msfc.domain import ModelInfo, RawVerdict
from msfc.vision import ClassicCvBaseline, Frame, InferenceOutput, Thresholds, generate_sample, postprocess


def _rng(seed: int = 0):
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------- ClassicCvBaseline
def test_baseline_requires_at_least_one_reference() -> None:
    with pytest.raises(VisionError, match="reference image"):
        ClassicCvBaseline(reference_images=[], defect_threshold=5.0)


def test_baseline_rejects_non_positive_threshold() -> None:
    ref = [generate_sample(_rng(), "GOOD")]
    with pytest.raises(VisionError, match="defect_threshold"):
        ClassicCvBaseline(reference_images=ref, defect_threshold=0.0)


def test_baseline_rejects_mismatched_reference_shapes() -> None:
    refs = [generate_sample(_rng(0), "GOOD"), generate_sample(_rng(1), "GOOD")[:64, :64]]
    with pytest.raises(VisionError, match="must all share one shape"):
        ClassicCvBaseline(reference_images=refs, defect_threshold=5.0)


def test_baseline_scores_a_good_image_low_and_a_mark_defect_high() -> None:
    good_refs = [generate_sample(_rng(seed), "GOOD") for seed in range(5)]
    engine = ClassicCvBaseline(reference_images=good_refs, defect_threshold=1.5)

    good_output = engine.predict(generate_sample(_rng(100), "GOOD"))
    defect_output = engine.predict(generate_sample(_rng(100), "DEFECT", "MARK"))

    assert good_output.class_scores["DEFECT"] < defect_output.class_scores["DEFECT"]
    assert "inference" in good_output.timings_ms and good_output.timings_ms["inference"] >= 0


def test_baseline_rejects_input_shape_mismatch() -> None:
    engine = ClassicCvBaseline(reference_images=[generate_sample(_rng(), "GOOD")], defect_threshold=1.0)
    with pytest.raises(VisionError, match="does not match"):
        engine.predict(np.zeros((10, 10, 3), dtype=np.uint8))


def test_inference_output_requires_defect_key() -> None:
    with pytest.raises(VisionError, match="DEFECT"):
        InferenceOutput(class_scores={"GOOD": 1.0}, timings_ms={"total": 1.0})


# --------------------------------------------------------------------------- postprocess
def _model() -> ModelInfo:
    return ModelInfo(name="test", version="0.0.1")


def test_postprocess_high_score_is_defect() -> None:
    output = InferenceOutput(class_scores={"GOOD": 0.1, "DEFECT": 0.9}, timings_ms={"inference": 2.0})
    result = postprocess(output, Thresholds(defect_at=0.5, uncertain_band=0.05), product_id="1-1", model=_model())
    assert result.verdict is RawVerdict.DEFECT
    assert result.confidence == pytest.approx(0.9)
    assert result.timings_ms["total"] == pytest.approx(2.0)


def test_postprocess_low_score_is_good() -> None:
    output = InferenceOutput(class_scores={"GOOD": 0.95, "DEFECT": 0.05}, timings_ms={"inference": 1.0})
    result = postprocess(output, Thresholds(defect_at=0.5, uncertain_band=0.05), product_id="1-1", model=_model())
    assert result.verdict is RawVerdict.GOOD
    assert result.confidence == pytest.approx(0.95)


def test_postprocess_score_in_the_band_is_uncertain() -> None:
    output = InferenceOutput(class_scores={"GOOD": 0.49, "DEFECT": 0.51}, timings_ms={"inference": 1.0})
    result = postprocess(output, Thresholds(defect_at=0.5, uncertain_band=0.05), product_id="1-1", model=_model())
    assert result.verdict is RawVerdict.UNCERTAIN
    assert result.confidence == pytest.approx(0.5)


def test_postprocess_boundary_is_inclusive_of_defect() -> None:
    """defect_score == upper bound counts as DEFECT (>=), not UNCERTAIN."""
    output = InferenceOutput(class_scores={"GOOD": 0.45, "DEFECT": 0.55}, timings_ms={"inference": 1.0})
    result = postprocess(output, Thresholds(defect_at=0.5, uncertain_band=0.05), product_id="1-1", model=_model())
    assert result.verdict is RawVerdict.DEFECT


def test_postprocess_carries_frame_seq_when_given() -> None:
    output = InferenceOutput(class_scores={"GOOD": 0.9, "DEFECT": 0.1}, timings_ms={"inference": 1.0})
    frame = Frame(image=np.zeros((4, 4, 3), dtype=np.uint8), seq=42, captured_mono_ms=0, source="t")
    result = postprocess(output, Thresholds(), product_id="1-1", model=_model(), frame=frame)
    assert result.frame_seq == 42


def test_postprocess_result_class_scores_are_copied_not_aliased() -> None:
    scores = {"GOOD": 0.9, "DEFECT": 0.1}
    output = InferenceOutput(class_scores=scores, timings_ms={"inference": 1.0})
    result = postprocess(output, Thresholds(), product_id="1-1", model=_model())
    scores["DEFECT"] = 0.99
    assert result.class_scores["DEFECT"] == 0.1


# --------------------------------------------------------------------------- Thresholds validation
@pytest.mark.parametrize("kwargs,match", [
    ({"defect_at": -0.1}, "defect_at"),
    ({"defect_at": 1.1}, "defect_at"),
    ({"uncertain_band": -0.01}, "uncertain_band"),
])
def test_thresholds_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(VisionError, match=match):
        Thresholds(**kwargs)
