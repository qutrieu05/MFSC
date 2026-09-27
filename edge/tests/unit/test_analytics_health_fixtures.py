"""P5.13 deterministic simulation (10 named scenarios, run through the full monitor pipeline)
+ P5.14's 15 named fixtures (the ones not already exactly one of the 10 scenarios) + relevant
P5.15 edge cases.
"""

from __future__ import annotations

import math

import pytest

from msfc.analytics.anomaly import AnomalyThresholds
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.health_models import (
    AnomalySeverity,
    HealthState,
    SensorMeasurement,
    SensorQuality,
    SensorType,
)
from msfc.analytics.health_monitor import MachineHealthMonitor
from msfc.analytics.predictive import RuleBasedReferenceModel
from msfc.analytics import health_simulate as sim

BASELINES = {
    "temp01": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80, unit="degC"),
    "current01": HealthBaseline(sensor_type=SensorType.CURRENT, expected_min=1.5, expected_max=2.5, unit="A"),
    "vib01": HealthBaseline(sensor_type=SensorType.VIBRATION, expected_min=0.5, expected_max=1.5, unit="mm/s"),
}
THRESHOLDS = {
    "temp01": AnomalyThresholds(warning_deviation=3, anomaly_deviation=10, critical_deviation=30,
                                 trend_rate_of_change_limit=0.003),
    "current01": AnomalyThresholds(warning_deviation=0.5, anomaly_deviation=2.0, critical_deviation=5.0,
                                    trend_rate_of_change_limit=0.0003),
    "vib01": AnomalyThresholds(warning_deviation=0.5, anomaly_deviation=2.0, critical_deviation=5.0,
                                trend_rate_of_change_limit=0.0003),
}


def _run(measurements, *, window_ms: int = 10_000):
    monitor = MachineHealthMonitor(baselines=BASELINES, thresholds=THRESHOLDS, window_ms=window_ms)
    flat = []
    if isinstance(measurements, dict):
        for series in measurements.values():
            flat.extend(series)
        flat.sort(key=lambda m: m.mono_ms)
    else:
        flat = list(measurements)
    last_t = 0
    for m in flat:
        monitor.ingest(m, mono_ms=m.mono_ms)
        last_t = m.mono_ms
    return monitor.snapshot(mono_ms=last_t)


# --------------------------------------------------------------------------- P5.13: 10 named scenarios
def test_scenario_1_3_normal_and_spike_temperature() -> None:
    assert _run(sim.scenario_normal_temperature()).health_state is HealthState.HEALTHY
    assert _run(sim.scenario_temperature_spike()).health_state is HealthState.CRITICAL


def test_scenario_2_rising_temperature() -> None:
    snap = _run(sim.scenario_rising_temperature())
    assert snap.health_state is HealthState.ANOMALY
    kinds = {a.kind for a in snap.active_anomalies}
    assert kinds == {"trend", "deviation"}


def test_scenario_4_6_current() -> None:
    assert _run(sim.scenario_normal_motor_current()).health_state is HealthState.HEALTHY
    assert _run(sim.scenario_increasing_motor_current()).health_state is HealthState.ANOMALY
    assert _run(sim.scenario_current_spike()).health_state is HealthState.CRITICAL


def test_scenario_7_9_vibration() -> None:
    assert _run(sim.scenario_normal_vibration()).health_state is HealthState.HEALTHY
    assert _run(sim.scenario_increasing_vibration()).health_state is HealthState.ANOMALY
    assert _run(sim.scenario_vibration_spike()).health_state is HealthState.CRITICAL


def test_scenario_10_sensor_failure() -> None:
    snap = _run(sim.scenario_sensor_failure())
    assert snap.health_state is HealthState.WARNING
    assert snap.active_anomalies[0].kind == "sensor_quality"


def test_scenario_11_missing_sensor_data() -> None:
    snap = _run(sim.scenario_missing_sensor_data())
    assert snap.health_state is HealthState.WARNING


def test_scenario_12_stale_sensor_data() -> None:
    snap = _run(sim.scenario_stale_sensor_data())
    assert snap.health_state is HealthState.WARNING


def test_scenario_13_multiple_simultaneous_anomalies() -> None:
    snap = _run(sim.scenario_multiple_simultaneous_anomalies())
    assert snap.health_state is HealthState.CRITICAL
    sensors_with_anomalies = {a.sensor_id for a in snap.active_anomalies}
    assert sensors_with_anomalies == {"temp01", "current01", "vib01"}


def test_scenario_14_recovery_after_anomaly() -> None:
    """A short window (2.5s) is used here specifically so the spike ages out and genuine
    recovery is observable by the end of the scenario (health_monitor.py documents this
    window-size/recovery-speed relationship)."""
    snap = _run(sim.scenario_recovery_after_anomaly(), window_ms=2_500)
    assert snap.health_state is HealthState.HEALTHY
    assert snap.active_anomalies == ()


def test_scenario_15_critical_machine_condition() -> None:
    snap = _run(sim.scenario_critical_machine_condition())
    assert snap.health_state is HealthState.CRITICAL
    assert len(snap.active_anomalies) == 6  # 3 sensors x (deviation + trend)


# --------------------------------------------------------------------------- P5.14: remaining named fixtures
def test_fixture_healthy_machine() -> None:
    assert _run(sim.scenario_normal_temperature()).health_state is HealthState.HEALTHY


def test_fixture_warning_condition_isolated() -> None:
    """A deviation just past the warning threshold (3) but below anomaly (10) -> WARNING only."""
    m = [SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=84.0, unit="degC")]
    snap = _run(m)
    assert snap.health_state is HealthState.WARNING


def test_fixture_anomaly_condition_isolated() -> None:
    """A deviation past anomaly (10) but below critical (30) -> ANOMALY only."""
    m = [SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=95.0, unit="degC")]
    snap = _run(m)
    assert snap.health_state is HealthState.ANOMALY


def test_fixture_critical_condition_isolated() -> None:
    snap = _run(sim.scenario_temperature_spike())
    assert snap.health_state is HealthState.CRITICAL


def test_fixture_cycle_time_anomaly() -> None:
    """P5.2 names cycle_time as a sensor type -- a CYCLE_TIME reading far outside a configured
    baseline is detected exactly like any other sensor (same code path, no special-casing)."""
    baselines = {"cycle01": HealthBaseline(sensor_type=SensorType.CYCLE_TIME, expected_min=900, expected_max=1100, unit="ms")}
    thresholds = {"cycle01": AnomalyThresholds(warning_deviation=50, anomaly_deviation=200, critical_deviation=1000)}
    monitor = MachineHealthMonitor(baselines=baselines, thresholds=thresholds, window_ms=10_000)
    monitor.ingest(SensorMeasurement(sensor_id="cycle01", sensor_type=SensorType.CYCLE_TIME, mono_ms=0,
                                      value=3000.0, unit="ms"), mono_ms=0)
    snap = monitor.snapshot(mono_ms=0)
    assert snap.health_state is not HealthState.HEALTHY
    assert snap.active_anomalies[0].sensor_type is SensorType.CYCLE_TIME


def test_fixture_invalid_measurement() -> None:
    """A NaN reading is tagged INVALID by quality assessment (msfc.analytics.quality) and
    excluded from feature statistics -- it must not silently corrupt the health assessment."""
    from msfc.analytics.quality import QualityConfig, build_measurement

    config = QualityConfig(expected_unit="degC")
    measurement = build_measurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, value=math.nan,
                                     unit="degC", mono_ms=0, now_mono_ms=0, config=config)
    assert measurement.quality is SensorQuality.INVALID
    snap = _run([measurement])
    # a single INVALID reading -> sample_count 0 for the feature, but the sensor_quality
    # detector still sees 1/1 bad readings and flags it
    assert snap.features["temp01"].sample_count == 0


def test_fixture_baseline_deviation() -> None:
    snap = _run(sim.scenario_rising_temperature())
    deviation_anomalies = [a for a in snap.active_anomalies if a.kind == "deviation"]
    assert len(deviation_anomalies) == 1


def test_fixture_trend_anomaly_isolated_from_deviation() -> None:
    """Values that stay INSIDE the baseline range the whole time, but change fast enough to
    trip the trend detector on their own -- proves trend and deviation are independent checks."""
    values = [60, 64, 68, 72, 76]  # all within [60, 80]; rate = 16/4000 = 0.004/ms > 0.003 limit
    measurements = [SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=i * 1000,
                                       value=v, unit="degC") for i, v in enumerate(values)]
    snap = _run(measurements)
    kinds = {a.kind for a in snap.active_anomalies}
    assert kinds == {"trend"}  # deviation must NOT also fire -- every value is in-range


def test_fixture_predictive_model_mock_result() -> None:
    model = RuleBasedReferenceModel(baselines=BASELINES, thresholds=THRESHOLDS)
    from msfc.analytics.features import extract_features

    measurements = [SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=0,
                                       value=150.0, unit="degC")]
    feature = extract_features(measurements, sensor_id="temp01", sensor_type=SensorType.TEMPERATURE,
                                window_start_mono_ms=0, window_end_mono_ms=0)
    result = model.predict({"temp01": feature}, mono_ms=0)
    assert result.predicted_state is HealthState.CRITICAL
    assert result.validated_on_real_data is False  # never claimed real-world-validated
