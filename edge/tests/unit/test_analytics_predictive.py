"""P5.11 predictive-model abstraction + P5.12 model input contract."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.anomaly import AnomalyThresholds
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.features import extract_features
from msfc.analytics.health_models import HealthState, SensorMeasurement, SensorType
from msfc.analytics.predictive import ModelInputContract, PredictiveHealthResult, RuleBasedReferenceModel

BASELINE = {"temp01": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)}
THRESHOLDS = {"temp01": AnomalyThresholds(warning_deviation=3, anomaly_deviation=10, critical_deviation=30)}


def _feature(values: list[float]):
    measurements = [SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=i * 1000,
                                       value=v, unit="degC") for i, v in enumerate(values)]
    return extract_features(measurements, sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                             window_start_mono_ms=0, window_end_mono_ms=(len(values) - 1) * 1000)


def test_predictive_result_rejects_out_of_range_risk_score() -> None:
    with pytest.raises(HealthError, match="risk_score"):
        PredictiveHealthResult(mono_ms=0, predicted_state=HealthState.HEALTHY, model_name="m", model_version="1",
                                risk_score=1.5)


def test_predictive_result_rejects_negative_rul() -> None:
    with pytest.raises(HealthError, match="remaining_useful_life_ms"):
        PredictiveHealthResult(mono_ms=0, predicted_state=HealthState.HEALTHY, model_name="m", model_version="1",
                                remaining_useful_life_ms=-1)


def test_predictive_result_defaults_to_not_validated() -> None:
    result = PredictiveHealthResult(mono_ms=0, predicted_state=HealthState.HEALTHY, model_name="m", model_version="1")
    assert result.validated_on_real_data is False


def test_rule_based_reference_model_is_never_marked_validated() -> None:
    model = RuleBasedReferenceModel(baselines=BASELINE, thresholds=THRESHOLDS)
    result = model.predict({"temp01": _feature([70, 71])}, mono_ms=1000)
    assert result.validated_on_real_data is False
    assert result.model_name == "rule-based-reference"


def test_rule_based_reference_model_never_estimates_rul() -> None:
    model = RuleBasedReferenceModel(baselines=BASELINE, thresholds=THRESHOLDS)
    result = model.predict({"temp01": _feature([70, 71])}, mono_ms=1000)
    assert result.remaining_useful_life_ms is None


def test_rule_based_reference_model_predicts_healthy_for_normal_data() -> None:
    model = RuleBasedReferenceModel(baselines=BASELINE, thresholds=THRESHOLDS)
    result = model.predict({"temp01": _feature([70, 71, 70])}, mono_ms=2000)
    assert result.predicted_state is HealthState.HEALTHY
    assert result.risk_score == pytest.approx(0.0)


def test_rule_based_reference_model_predicts_critical_for_a_spike() -> None:
    model = RuleBasedReferenceModel(baselines=BASELINE, thresholds=THRESHOLDS)
    result = model.predict({"temp01": _feature([70, 70, 150])}, mono_ms=2000)
    assert result.predicted_state is HealthState.CRITICAL
    assert result.risk_score > 0.0


def test_model_ignores_sensors_without_a_configured_baseline() -> None:
    model = RuleBasedReferenceModel(baselines={}, thresholds={})
    result = model.predict({"temp01": _feature([999])}, mono_ms=0)
    assert result.predicted_state is HealthState.HEALTHY  # unconfigured sensor -> not judged


def test_model_input_contract_documents_the_interface() -> None:
    contract = ModelInputContract(
        feature_names=("mean", "std_dev", "rate_of_change"),
        units={"mean": "degC", "std_dev": "degC", "rate_of_change": "degC/ms"},
        expected_ranges={"mean": (60.0, 80.0)},
        timestamp_semantics="mono_ms of the feature window's end",
        missing_data_behavior="feature omitted (None) when sample_count == 0",
        normalization="none applied here",
        model_version="0.1-unvalidated",
        output_format="PredictiveHealthResult",
    )
    assert "mean" in contract.feature_names
    assert contract.units["mean"] == "degC"
