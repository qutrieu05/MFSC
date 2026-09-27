"""Predictive-maintenance model abstraction (P5.11) and input contract (P5.12).

CRITICAL, per the PO's explicit instruction: this module does NOT train anything. There is no
real machine dataset to train on, and Phase 5 must not claim real-world predictive accuracy.
:class:`RuleBasedReferenceModel` is a deterministic, rule-based reference implementation of
the :class:`PredictiveHealthModel` interface -- built from the SAME anomaly-detection logic
:mod:`msfc.analytics.anomaly` already uses, not a trained model of any kind -- so
``PredictiveHealthResult.validated_on_real_data`` is always ``False`` for it, and the class
docstring says so plainly. A future real model (Isolation Forest, an autoencoder, a supervised
classifier, whatever real data eventually justifies) only needs to implement the same
Protocol; nothing in :mod:`msfc.analytics.health_monitor` needs to change (P5.11: "must allow
a real trained model to replace the mock without rewriting the monitoring layer").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from msfc.core.errors import HealthError
from msfc.analytics.anomaly import AnomalyThresholds, detect_baseline_anomaly
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.health_models import FeatureSet, HealthState
from msfc.analytics.health_score import compute_health_score


@dataclass(frozen=True, slots=True)
class ModelInputContract:
    """P5.12 -- documents, for any future real model, exactly what it will be given. Not
    itself validated against any real model; a real integration would extend/adjust this."""

    feature_names: tuple[str, ...]
    units: dict[str, str]
    expected_ranges: dict[str, tuple[float, float]]
    timestamp_semantics: str  # e.g. "mono_ms of the feature window's end, device-local clock"
    missing_data_behavior: str  # e.g. "a feature is omitted (not zero-filled) when sample_count==0"
    normalization: str  # e.g. "none applied here -- a real model's own pipeline must normalize"
    model_version: str
    output_format: str  # e.g. "PredictiveHealthResult: predicted_state, risk_score in [0,1], RUL optional"


@dataclass(frozen=True, slots=True)
class PredictiveHealthResult:
    mono_ms: int
    predicted_state: HealthState
    model_name: str
    model_version: str
    risk_score: float | None = None  # 0 (no risk) .. 1 (high risk); None if the model doesn't estimate it
    remaining_useful_life_ms: int | None = None  # None if the model doesn't estimate RUL
    validated_on_real_data: bool = False  # NEVER True for anything shipped in this phase

    def __post_init__(self) -> None:
        if self.risk_score is not None and not (0.0 <= self.risk_score <= 1.0):
            raise HealthError(f"risk_score must be in [0, 1], got {self.risk_score!r}")
        if self.remaining_useful_life_ms is not None and self.remaining_useful_life_ms < 0:
            raise HealthError(f"remaining_useful_life_ms must be >= 0, got {self.remaining_useful_life_ms!r}")


class PredictiveHealthModel(Protocol):
    name: str
    version: str

    def predict(self, features: Mapping[str, FeatureSet], *, mono_ms: int) -> PredictiveHealthResult: ...


class RuleBasedReferenceModel:
    """NOT A TRAINED MODEL. NOT VALIDATED ON REAL MACHINE DATA.

    A deterministic reference implementation of :class:`PredictiveHealthModel`, built from
    the same rule-based anomaly detection the rest of msfc.analytics uses -- it exists so the
    architecture (feature dict in, PredictiveHealthResult out) is exercised end to end, and so
    a real model has a working baseline to be swapped in against, not because this rule-based
    approach is being proposed as the production predictive-maintenance algorithm.
    """

    name = "rule-based-reference"
    version = "0.1-unvalidated"

    def __init__(self, *, baselines: dict[str, HealthBaseline], thresholds: dict[str, AnomalyThresholds]) -> None:
        self._baselines = dict(baselines)
        self._thresholds = dict(thresholds)

    def predict(self, features: Mapping[str, FeatureSet], *, mono_ms: int) -> PredictiveHealthResult:
        anomalies = []
        for sensor_id, feature in features.items():
            baseline = self._baselines.get(sensor_id)
            thresholds = self._thresholds.get(sensor_id)
            if baseline is None or thresholds is None:
                continue
            result = detect_baseline_anomaly(feature, baseline, thresholds)
            if result is not None:
                anomalies.append(result)
        score = compute_health_score(anomalies)
        risk_score = 1.0 - score.value
        return PredictiveHealthResult(
            mono_ms=mono_ms, predicted_state=score.state, model_name=self.name, model_version=self.version,
            risk_score=risk_score, remaining_useful_life_ms=None,  # never estimated -- no real degradation data
            validated_on_real_data=False,
        )
