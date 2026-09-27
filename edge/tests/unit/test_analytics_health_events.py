"""P5.9 machine-health event factories."""

from __future__ import annotations

from msfc.analytics.health_events import from_anomaly, from_health_score_change, from_health_state_change, from_measurement
from msfc.analytics.health_models import (
    AnomalyResult,
    AnomalySeverity,
    HealthEventType,
    HealthScore,
    HealthState,
    SensorMeasurement,
    SensorQuality,
    SensorType,
)


def test_from_measurement_ok_is_sensor_reading() -> None:
    m = SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=70.0, unit="degC")
    event = from_measurement(m)
    assert event.type is HealthEventType.SENSOR_READING
    assert event.sensor_id == "s1"


def test_from_measurement_bad_quality_is_sensor_fault() -> None:
    m = SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=0.0, unit="degC",
                           quality=SensorQuality.MISSING)
    event = from_measurement(m)
    assert event.type is HealthEventType.SENSOR_FAULT


def test_from_anomaly_detected() -> None:
    anomaly = AnomalyResult(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=100,
                            severity=AnomalySeverity.CRITICAL, kind="deviation", reason="too hot")
    event = from_anomaly(anomaly)
    assert event.type is HealthEventType.ANOMALY_DETECTED
    assert event.detail["severity"] == "CRITICAL"


def test_from_anomaly_cleared() -> None:
    anomaly = AnomalyResult(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=100,
                            severity=AnomalySeverity.WARNING, kind="deviation", reason="ok now")
    event = from_anomaly(anomaly, cleared=True)
    assert event.type is HealthEventType.ANOMALY_CLEARED


def test_state_change_always_yields_health_state_changed() -> None:
    events = from_health_state_change(HealthState.HEALTHY, HealthState.HEALTHY, mono_ms=0)
    assert len(events) == 1
    assert events[0].type is HealthEventType.HEALTH_STATE_CHANGED


def test_entering_warning_yields_dedicated_event() -> None:
    events = from_health_state_change(HealthState.HEALTHY, HealthState.WARNING, mono_ms=0)
    types = {e.type for e in events}
    assert HealthEventType.MACHINE_HEALTH_WARNING in types


def test_entering_critical_yields_dedicated_event() -> None:
    events = from_health_state_change(HealthState.WARNING, HealthState.CRITICAL, mono_ms=0)
    types = {e.type for e in events}
    assert HealthEventType.MACHINE_HEALTH_CRITICAL in types


def test_staying_in_warning_does_not_refire_dedicated_event() -> None:
    events = from_health_state_change(HealthState.WARNING, HealthState.WARNING, mono_ms=0)
    types = {e.type for e in events}
    assert HealthEventType.MACHINE_HEALTH_WARNING not in types


def test_from_health_score_change() -> None:
    old = HealthScore(value=1.0, state=HealthState.HEALTHY)
    new = HealthScore(value=0.5, state=HealthState.ANOMALY)
    event = from_health_score_change(old, new, mono_ms=50)
    assert event.type is HealthEventType.HEALTH_SCORE_CHANGED
    assert event.detail == {"from": 1.0, "to": 0.5}
