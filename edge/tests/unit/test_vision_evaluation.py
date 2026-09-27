"""Tests for msfc.vision.evaluation.evaluate (VT-01..04 groundwork).

Uses the synthetic generator plus ClassicCvBaseline end-to-end — this is the same pipeline
P1.11 will point at a real dataset, just fed 0-VND synthetic data for now (D-026: results
here are never a claim about real products, only about the pipeline's own correctness).
"""

from __future__ import annotations

import numpy as np
import pytest

from msfc.core.errors import VisionError
from msfc.vision import ClassicCvBaseline, RoiConfig, Thresholds, evaluate, generate_dataset, generate_sample


def _engine(seed: int = 0) -> ClassicCvBaseline:
    refs = [generate_sample(np.random.default_rng(s), "GOOD") for s in range(seed, seed + 8)]
    return ClassicCvBaseline(reference_images=refs, defect_threshold=1.2)


def _roi() -> RoiConfig:
    return RoiConfig(x=0, y=0, width=128, height=128, target_size=(128, 128))


def test_evaluate_rejects_empty_samples() -> None:
    with pytest.raises(VisionError, match="at least one sample"):
        evaluate([], _engine(), Thresholds(), roi=_roi(), data_source="synthetic")


def test_evaluate_rejects_unknown_data_source() -> None:
    samples = generate_dataset(seed=0, n_good=2, n_defect_per_sub_label=1, session_id="s01")
    with pytest.raises(VisionError, match="data_source"):
        evaluate(samples, _engine(), Thresholds(), roi=_roi(), data_source="bogus")


def test_evaluate_rejects_unknown_uncertain_policy() -> None:
    samples = generate_dataset(seed=0, n_good=2, n_defect_per_sub_label=1, session_id="s01")
    with pytest.raises(VisionError, match="uncertain_policy"):
        evaluate(samples, _engine(), Thresholds(), roi=_roi(), data_source="synthetic",
                  uncertain_policy="bogus")


def test_evaluate_report_is_tagged_synthetic() -> None:
    samples = generate_dataset(seed=0, n_good=5, n_defect_per_sub_label=2, session_id="s01")
    report = evaluate(samples, _engine(), Thresholds(defect_at=0.5, uncertain_band=0.02),
                       roi=_roi(), data_source="synthetic")
    assert report.data_source == "synthetic"
    assert report.is_synthetic is True
    assert report.n_samples == len(samples)


def test_evaluate_confusion_matrix_sums_to_n_samples() -> None:
    samples = generate_dataset(seed=1, n_good=10, n_defect_per_sub_label=5, session_id="s01")
    report = evaluate(samples, _engine(seed=10), Thresholds(defect_at=0.5, uncertain_band=0.02),
                       roi=_roi(), data_source="synthetic")
    assert sum(report.confusion.values()) == report.n_samples


def test_evaluate_recall_by_sub_label_covers_every_defect_type() -> None:
    from msfc.vision import DEFECT_SUB_LABELS
    samples = generate_dataset(seed=2, n_good=5, n_defect_per_sub_label=5, session_id="s01")
    report = evaluate(samples, _engine(seed=20), Thresholds(defect_at=0.5, uncertain_band=0.02),
                       roi=_roi(), data_source="synthetic")
    assert set(report.recall_by_sub_label) == set(DEFECT_SUB_LABELS)
    for recall in report.recall_by_sub_label.values():
        assert 0.0 <= recall <= 1.0


def test_evaluate_easy_defect_recall_is_at_least_as_good_as_hard_defect_recall() -> None:
    """MARK (large, dark) must be at least as easy to catch as SCRATCH (subtle, low
    contrast) for this baseline — if this stops holding it means the synthetic generator or
    the baseline changed in a way that breaks the intended easy/medium/hard ordering."""
    samples = generate_dataset(seed=3, n_good=0, n_defect_per_sub_label=30, session_id="s01")
    report = evaluate(samples, _engine(seed=30), Thresholds(defect_at=0.5, uncertain_band=0.0),
                       roi=_roi(), data_source="synthetic")
    assert report.recall_by_sub_label["MARK"] >= report.recall_by_sub_label["SCRATCH"]


def test_evaluate_false_positive_and_negative_ids_are_consistent_with_confusion() -> None:
    samples = generate_dataset(seed=4, n_good=10, n_defect_per_sub_label=5, session_id="s01")
    report = evaluate(samples, _engine(seed=40), Thresholds(defect_at=0.5, uncertain_band=0.02),
                       roi=_roi(), data_source="synthetic")
    assert len(report.false_positive_ids) == report.confusion["fp"]
    assert len(report.false_negative_ids) == report.confusion["fn"]
    for idx in report.false_positive_ids:
        assert samples[idx].label == "GOOD"
    for idx in report.false_negative_ids:
        assert samples[idx].label == "DEFECT"


class _AlwaysBorderlineEngine:
    """Fake engine that always scores exactly at the decision threshold, so every sample is
    UNCERTAIN regardless of what the real baseline would say — isolates evaluate()'s
    uncertain_policy handling from ClassicCvBaseline's actual (data-dependent) confidence."""

    name = "always_borderline"
    version = "0.0.1"

    def predict(self, image):
        from msfc.vision import InferenceOutput
        return InferenceOutput(class_scores={"GOOD": 0.5, "DEFECT": 0.5}, timings_ms={"inference": 0.0})


def test_evaluate_uncertain_policy_as_good_vs_as_defect_changes_recall() -> None:
    """Every sample lands exactly on the threshold (UNCERTAIN); 'as_good' must then score
    every DEFECT sample as a miss, while 'as_defect' scores it correct."""
    samples = generate_dataset(seed=5, n_good=0, n_defect_per_sub_label=20, session_id="s01")
    thresholds = Thresholds(defect_at=0.5, uncertain_band=0.01)
    engine = _AlwaysBorderlineEngine()

    as_defect = evaluate(samples, engine, thresholds, roi=_roi(),
                          data_source="synthetic", uncertain_policy="as_defect")
    as_good = evaluate(samples, engine, thresholds, roi=_roi(),
                        data_source="synthetic", uncertain_policy="as_good")

    assert as_defect.uncertain_count == as_good.uncertain_count == len(samples)
    assert as_defect.recall_defect == 1.0
    assert as_good.recall_defect == 0.0


def test_evaluate_latency_report_has_all_four_keys() -> None:
    samples = generate_dataset(seed=6, n_good=5, n_defect_per_sub_label=2, session_id="s01")
    report = evaluate(samples, _engine(seed=60), Thresholds(), roi=_roi(), data_source="synthetic")
    assert set(report.latency_ms) == {"mean", "p50", "p95", "max"}
    assert report.latency_ms["max"] >= report.latency_ms["p95"] >= report.latency_ms["p50"]
