"""P5.6 deterministic anomaly detection + P5.8 severity combination."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.anomaly import (
    AnomalyThresholds,
    combine_anomalies,
    detect_baseline_anomaly,
    detect_quality_anomaly,
    detect_trend_anomaly,
)
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.features import extract_features
from msfc.analytics.health_models import AnomalyResult, AnomalySeverity, HealthState, SensorMeasurement, SensorQuality, SensorType

BASELINE = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)
THRESHOLDS = AnomalyThresholds(warning_deviation=3, anomaly_deviation=10, critical_deviation=30,
                                trend_rate_of_change_limit=0.003)


def _m(value: float, mono_ms: int, quality: SensorQuality = SensorQuality.OK) -> SensorMeasurement:
    return SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=mono_ms,
                              value=value, unit="degC", quality=quality)


def _feature(values: list[float]):
    measurements = [_m(v, i * 1000) for i, v in enumerate(values)]
    return extract_features(measurements, sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                             window_start_mono_ms=0, window_end_mono_ms=(len(values) - 1) * 1000)


def test_thresholds_reject_out_of_order_values() -> None:
    with pytest.raises(HealthError, match="thresholds must satisfy"):
        AnomalyThresholds(warning_deviation=10, anomaly_deviation=3, critical_deviation=30)


def test_thresholds_reject_bad_quality_ratio() -> None:
    with pytest.raises(HealthError, match="max_bad_quality_ratio"):
        AnomalyThresholds(warning_deviation=1, anomaly_deviation=2, critical_deviation=3, max_bad_quality_ratio=1.5)


# --------------------------------------------------------------------------- baseline (threshold/deviation)
def test_baseline_anomaly_none_when_within_range() -> None:
    feature = _feature([70, 71, 70, 69])
    assert detect_baseline_anomaly(feature, BASELINE, THRESHOLDS) is None


def test_baseline_anomaly_uses_the_extreme_value_not_the_mean() -> None:
    """The bug this regression-guards: averaging a brief spike with 6 normal readings would
    dilute it below any reasonable threshold."""
    feature = _feature([70, 70, 70, 150, 70, 70, 70])
    result = detect_baseline_anomaly(feature, BASELINE, THRESHOLDS)
    assert result is not None
    assert result.value == 150
    assert result.severity is AnomalySeverity.CRITICAL


def test_baseline_anomaly_severity_scales_with_deviation() -> None:
    warning = detect_baseline_anomaly(_feature([84]), BASELINE, THRESHOLDS)  # deviation=4
    anomaly = detect_baseline_anomaly(_feature([95]), BASELINE, THRESHOLDS)  # deviation=15
    critical = detect_baseline_anomaly(_feature([200]), BASELINE, THRESHOLDS)  # deviation=120
    assert warning.severity is AnomalySeverity.WARNING
    assert anomaly.severity is AnomalySeverity.ANOMALY
    assert critical.severity is AnomalySeverity.CRITICAL


def test_baseline_anomaly_detects_low_side_too() -> None:
    result = detect_baseline_anomaly(_feature([10]), BASELINE, THRESHOLDS)
    assert result is not None
    assert result.value == 10


def test_baseline_anomaly_none_for_empty_feature() -> None:
    empty = extract_features([], sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                              window_start_mono_ms=0, window_end_mono_ms=1000)
    assert detect_baseline_anomaly(empty, BASELINE, THRESHOLDS) is None


# --------------------------------------------------------------------------- trend
def test_trend_anomaly_none_without_a_configured_limit() -> None:
    thresholds_no_trend = AnomalyThresholds(warning_deviation=3, anomaly_deviation=10, critical_deviation=30)
    feature = _feature([60, 70, 80, 90, 100])
    assert detect_trend_anomaly(feature, thresholds_no_trend) is None


def test_trend_anomaly_fires_when_rate_of_change_exceeds_limit() -> None:
    feature = _feature([60, 70, 80, 90, 100])  # rate = 40/4000 = 0.01/ms
    result = detect_trend_anomaly(feature, THRESHOLDS)
    assert result is not None
    assert result.kind == "trend"
    assert result.severity is AnomalySeverity.WARNING


def test_trend_anomaly_none_for_slow_change() -> None:
    feature = _feature([70, 70.1, 70.2, 70.3])
    assert detect_trend_anomaly(feature, THRESHOLDS) is None


# --------------------------------------------------------------------------- sensor quality
def test_quality_anomaly_fires_when_bad_ratio_exceeds_limit() -> None:
    measurements = [_m(70, 0), _m(0, 1000, quality=SensorQuality.INVALID), _m(0, 2000, quality=SensorQuality.MISSING)]
    result = detect_quality_anomaly(measurements, sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                                     mono_ms=2000, thresholds=THRESHOLDS)
    assert result is not None
    assert result.kind == "sensor_quality"


def test_quality_anomaly_none_when_mostly_ok() -> None:
    measurements = [_m(70, 0), _m(71, 1000), _m(0, 2000, quality=SensorQuality.MISSING)]
    result = detect_quality_anomaly(measurements, sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                                     mono_ms=2000, thresholds=THRESHOLDS)
    assert result is None  # 1/3 bad < 0.5 default max_bad_quality_ratio


def test_quality_anomaly_none_for_empty_measurements() -> None:
    result = detect_quality_anomaly([], sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                                     mono_ms=0, thresholds=THRESHOLDS)
    assert result is None


# --------------------------------------------------------------------------- combine (P5.8)
def test_combine_no_anomalies_is_healthy() -> None:
    assert combine_anomalies([]) is HealthState.HEALTHY


def test_combine_takes_the_maximum_severity() -> None:
    """P5.8's own example: WARNING + CRITICAL + ANOMALY simultaneously -> CRITICAL."""
    anomalies = [
        AnomalyResult(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=0,
                      severity=AnomalySeverity.WARNING, kind="deviation", reason="r1"),
        AnomalyResult(sensor_id="current01", sensor_type=SensorType.CURRENT, mono_ms=0,
                      severity=AnomalySeverity.CRITICAL, kind="deviation", reason="r2"),
        AnomalyResult(sensor_id="vib01", sensor_type=SensorType.VIBRATION, mono_ms=0,
                      severity=AnomalySeverity.ANOMALY, kind="deviation", reason="r3"),
    ]
    assert combine_anomalies(anomalies) is HealthState.CRITICAL


def test_combine_single_anomaly_maps_directly() -> None:
    anomaly = AnomalyResult(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=0,
                            severity=AnomalySeverity.ANOMALY, kind="deviation", reason="r")
    assert combine_anomalies([anomaly]) is HealthState.ANOMALY
