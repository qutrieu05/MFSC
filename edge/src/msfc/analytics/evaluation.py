"""Model evaluation framework (P5.21).

FRAMEWORK ONLY. Every metric here is verified against hand-computed numbers in tests; none is
ever run against msfc.analytics.health_simulate's synthetic fixtures and reported as if it
were a real accuracy figure (P5.21: "do NOT report meaningful real-world metrics from
synthetic fixtures as if they represent production performance"). ROC-AUC/PR-AUC are not
implemented this round -- both need a full threshold sweep over a *scored* classifier, and
there is no real scored classifier yet to evaluate; deferred until one exists (see D-053).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from msfc.core.errors import HealthError


@dataclass(frozen=True, slots=True)
class ClassificationMetrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    def __post_init__(self) -> None:
        for name in ("true_positive", "false_positive", "true_negative", "false_negative"):
            if getattr(self, name) < 0:
                raise HealthError(f"{name} must be >= 0")

    @property
    def precision(self) -> float | None:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def false_positive_rate(self) -> float | None:
        denom = self.false_positive + self.true_negative
        return self.false_positive / denom if denom else None

    @property
    def false_negative_rate(self) -> float | None:
        denom = self.false_negative + self.true_positive
        return self.false_negative / denom if denom else None


def evaluate_detections(predicted: Sequence[bool], actual: Sequence[bool]) -> ClassificationMetrics:
    if len(predicted) != len(actual):
        raise HealthError(f"predicted ({len(predicted)}) and actual ({len(actual)}) must be the same length")
    tp = fp = tn = fn = 0
    for p, a in zip(predicted, actual):
        if p and a:
            tp += 1
        elif p and not a:
            fp += 1
        elif not p and not a:
            tn += 1
        else:
            fn += 1
    return ClassificationMetrics(tp, fp, tn, fn)


@dataclass(frozen=True, slots=True)
class RegressionMetrics:
    """For a future RUL (remaining-useful-life) model."""

    mae: float
    rmse: float


def evaluate_regression(predicted: Sequence[float], actual: Sequence[float]) -> RegressionMetrics:
    if len(predicted) != len(actual):
        raise HealthError(f"predicted ({len(predicted)}) and actual ({len(actual)}) must be the same length")
    if not predicted:
        raise HealthError("predicted/actual must not be empty")
    errors = [p - a for p, a in zip(predicted, actual)]
    mae = sum(abs(e) for e in errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    return RegressionMetrics(mae=mae, rmse=rmse)


def evaluate_detection_delay(*, anomaly_onset_mono_ms: int, first_detected_mono_ms: int | None) -> int | None:
    """None when the anomaly was never detected at all -- never a fake/negative delay."""
    if first_detected_mono_ms is None:
        return None
    if first_detected_mono_ms < anomaly_onset_mono_ms:
        raise HealthError("first_detected_mono_ms must not be before anomaly_onset_mono_ms")
    return first_detected_mono_ms - anomaly_onset_mono_ms
