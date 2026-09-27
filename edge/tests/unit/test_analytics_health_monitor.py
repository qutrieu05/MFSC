"""P5.10 machine health monitor — orchestrates quality (pre-tagged) -> features -> baseline ->
anomaly detection -> scoring, and P5.15 edge cases specific to the monitor (sensor with no
configured thresholds, anomaly clearing, health-state transition events)."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.anomaly import AnomalyThresholds
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.health_events import HealthEventType
from msfc.analytics.health_models import HealthState, SensorMeasurement, SensorType
from msfc.analytics.health_monitor import MachineHealthMonitor

BASELINE = {"temp01": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)}
THRESHOLDS = {"temp01": AnomalyThresholds(warning_deviation=3, anomaly_deviation=10, critical_deviation=30,
                                           trend_rate_of_change_limit=0.003)}


def _m(value: float, mono_ms: int) -> SensorMeasurement:
    return SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=mono_ms,
                              value=value, unit="degC")


def test_monitor_rejects_non_positive_window() -> None:
    with pytest.raises(HealthError, match="window_ms"):
        MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=0)


def test_fresh_monitor_snapshot_is_unknown() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    snap = monitor.snapshot(mono_ms=0)
    assert snap.health_state is HealthState.UNKNOWN
    assert snap.active_anomalies == ()


def test_normal_readings_stay_healthy() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    for i, v in enumerate([70, 71, 70, 69]):
        monitor.ingest(_m(v, i * 1000), mono_ms=i * 1000)
    snap = monitor.snapshot(mono_ms=3000)
    assert snap.health_state is HealthState.HEALTHY
    assert snap.active_anomalies == ()


def test_spike_is_detected_and_raises_state() -> None:
    """A spike at the end of the window drives both the deviation check (the extreme value
    itself) AND the trend check (rate_of_change is measured first-to-last across the whole
    window, and a sudden jump IS a high rate of change) -- both legitimately fire together."""
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    for i, v in enumerate([70, 70, 70, 150]):
        monitor.ingest(_m(v, i * 1000), mono_ms=i * 1000)
    snap = monitor.snapshot(mono_ms=3000)
    assert snap.health_state is HealthState.CRITICAL
    kinds = {a.kind for a in snap.active_anomalies}
    assert "deviation" in kinds


def test_sensor_without_configured_thresholds_is_never_judged() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds={}, window_ms=10_000)
    monitor.ingest(_m(999, 0), mono_ms=0)  # wildly out of baseline range
    snap = monitor.snapshot(mono_ms=0)
    assert snap.active_anomalies == ()  # no thresholds configured -> not evaluated at all
    assert snap.health_state is HealthState.HEALTHY  # zero anomalies observed -> healthy, not a false CRITICAL


def test_anomaly_ages_out_of_a_short_window() -> None:
    """A spike stops being reported once the window has moved past it -- window_ms directly
    controls recovery speed (documented in health_monitor.py's own docstring)."""
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=2_500)
    readings = [70, 70, 150, 150, 70, 70, 70]
    for i, v in enumerate(readings):
        monitor.ingest(_m(v, i * 1000), mono_ms=i * 1000)
    snap = monitor.snapshot(mono_ms=(len(readings) - 1) * 1000)
    assert snap.health_state is HealthState.HEALTHY  # the spike has aged out of the 2.5s window


def test_drain_events_returns_and_clears() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    monitor.ingest(_m(70, 0), mono_ms=0)
    events = monitor.drain_events()
    assert len(events) >= 1
    assert monitor.drain_events() == ()  # cleared after drain


def test_entering_critical_produces_a_dedicated_event() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    monitor.ingest(_m(70, 0), mono_ms=0)
    monitor.drain_events()
    monitor.ingest(_m(150, 1000), mono_ms=1000)
    events = monitor.drain_events()
    types = {e.type for e in events}
    assert HealthEventType.MACHINE_HEALTH_CRITICAL in types


def test_out_of_order_ingest_is_rejected() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    monitor.ingest(_m(70, 5000), mono_ms=5000)
    with pytest.raises(HealthError, match="out-of-order"):
        monitor.ingest(_m(71, 4000), mono_ms=4000)


def test_snapshot_exposes_latest_measurement_and_features() -> None:
    monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    monitor.ingest(_m(70, 0), mono_ms=0)
    monitor.ingest(_m(75, 1000), mono_ms=1000)
    snap = monitor.snapshot(mono_ms=1000)
    assert snap.latest_measurements["temp01"].value == 75
    assert snap.features["temp01"].sample_count == 2
