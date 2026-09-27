"""P5.21 model evaluation framework — verified against hand-computed numbers only; never run
against synthetic health fixtures and reported as a real accuracy claim (see module docstring
in msfc.analytics.evaluation)."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.evaluation import evaluate_detection_delay, evaluate_detections, evaluate_regression


def test_evaluate_detections_rejects_mismatched_lengths() -> None:
    with pytest.raises(HealthError, match="same length"):
        evaluate_detections([True], [True, False])


def test_evaluate_detections_perfect_classifier() -> None:
    metrics = evaluate_detections([True, False, True, False], [True, False, True, False])
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0
    assert metrics.false_positive_rate == 0.0
    assert metrics.false_negative_rate == 0.0


def test_evaluate_detections_hand_computed() -> None:
    # predicted: T T F F ; actual: T F T F -> tp=1, fp=1, tn=1, fn=1
    metrics = evaluate_detections([True, True, False, False], [True, False, True, False])
    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.true_negative == 1
    assert metrics.false_negative == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1 == pytest.approx(0.5)


def test_evaluate_detections_no_positive_predictions_gives_none_precision() -> None:
    metrics = evaluate_detections([False, False], [True, False])
    assert metrics.precision is None  # 0/0 undefined, not a fake 0.0 or 1.0
    assert metrics.recall == 0.0


def test_classification_metrics_rejects_negative_counts() -> None:
    from msfc.analytics.evaluation import ClassificationMetrics
    with pytest.raises(HealthError):
        ClassificationMetrics(true_positive=-1, false_positive=0, true_negative=0, false_negative=0)


def test_evaluate_regression_rejects_mismatched_lengths() -> None:
    with pytest.raises(HealthError, match="same length"):
        evaluate_regression([1.0], [1.0, 2.0])


def test_evaluate_regression_rejects_empty_input() -> None:
    with pytest.raises(HealthError, match="empty"):
        evaluate_regression([], [])


def test_evaluate_regression_perfect_prediction() -> None:
    metrics = evaluate_regression([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert metrics.mae == 0.0
    assert metrics.rmse == 0.0


def test_evaluate_regression_hand_computed() -> None:
    # errors: 1, -1 -> MAE = 1.0, RMSE = 1.0
    metrics = evaluate_regression([2.0, 1.0], [1.0, 2.0])
    assert metrics.mae == pytest.approx(1.0)
    assert metrics.rmse == pytest.approx(1.0)


def test_evaluate_detection_delay_never_detected_is_none() -> None:
    assert evaluate_detection_delay(anomaly_onset_mono_ms=1000, first_detected_mono_ms=None) is None


def test_evaluate_detection_delay_computes_gap() -> None:
    assert evaluate_detection_delay(anomaly_onset_mono_ms=1000, first_detected_mono_ms=1500) == 500


def test_evaluate_detection_delay_rejects_detection_before_onset() -> None:
    with pytest.raises(HealthError, match="must not be before"):
        evaluate_detection_delay(anomaly_onset_mono_ms=1000, first_detected_mono_ms=500)
