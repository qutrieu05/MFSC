"""P5.1 machine-health domain model."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.health_models import (
    AnomalySeverity,
    HealthEvent,
    HealthEventType,
    HealthScore,
    HealthState,
    SensorMeasurement,
    SensorQuality,
    SensorType,
)


def test_sensor_type_is_a_superset_of_the_draft_schema_three() -> None:
    values = {t.value for t in SensorType}
    assert {"temperature", "vibration", "current"} <= values
    assert len(values) == 8  # D-051: intentionally broader than health_features.v1's draft 3


def test_health_state_has_five_values_per_this_rounds_directive() -> None:
    assert {s.value for s in HealthState} == {"HEALTHY", "WARNING", "ANOMALY", "CRITICAL", "UNKNOWN"}


def test_sensor_measurement_rejects_negative_mono_ms() -> None:
    with pytest.raises(HealthError, match="mono_ms"):
        SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=-1, value=1.0, unit="degC")


def test_sensor_measurement_rejects_empty_sensor_id() -> None:
    with pytest.raises(HealthError, match="sensor_id"):
        SensorMeasurement(sensor_id="", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=1.0, unit="degC")


def test_sensor_measurement_defaults_to_ok_quality() -> None:
    m = SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=70.0, unit="degC")
    assert m.quality is SensorQuality.OK


def test_anomaly_severity_rank_is_ordered() -> None:
    assert AnomalySeverity.INFO.rank < AnomalySeverity.WARNING.rank
    assert AnomalySeverity.WARNING.rank < AnomalySeverity.ANOMALY.rank
    assert AnomalySeverity.ANOMALY.rank < AnomalySeverity.CRITICAL.rank


def test_health_score_rejects_out_of_range_value() -> None:
    with pytest.raises(HealthError, match="value"):
        HealthScore(value=1.5, state=HealthState.HEALTHY)
    with pytest.raises(HealthError, match="value"):
        HealthScore(value=-0.1, state=HealthState.HEALTHY)


def test_health_score_accepts_boundary_values() -> None:
    HealthScore(value=0.0, state=HealthState.CRITICAL)
    HealthScore(value=1.0, state=HealthState.HEALTHY)


def test_health_event_rejects_negative_mono_ms() -> None:
    with pytest.raises(HealthError, match="mono_ms"):
        HealthEvent(type=HealthEventType.SENSOR_READING, mono_ms=-1)


def test_health_event_type_is_exactly_the_po_named_events() -> None:
    assert {e.value for e in HealthEventType} == {
        "sensor_reading", "anomaly_detected", "anomaly_cleared", "health_state_changed",
        "health_score_changed", "sensor_fault", "machine_health_warning", "machine_health_critical",
    }
