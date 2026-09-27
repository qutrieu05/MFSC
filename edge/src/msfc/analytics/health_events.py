"""Machine-health event factories (P5.9) — builds HealthEvent from the domain objects the rest
of this module produces (SensorMeasurement, AnomalyResult, HealthState/HealthScore
transitions), the same "factory function from an existing object" pattern as
msfc.analytics.events (P4.3).
"""

from __future__ import annotations

from msfc.analytics.health_models import (
    AnomalyResult,
    HealthEvent,
    HealthEventType,
    HealthScore,
    HealthState,
    SensorMeasurement,
    SensorQuality,
)


def from_measurement(measurement: SensorMeasurement) -> HealthEvent:
    event_type = (HealthEventType.SENSOR_FAULT if measurement.quality is not SensorQuality.OK
                  else HealthEventType.SENSOR_READING)
    return HealthEvent(type=event_type, mono_ms=measurement.mono_ms, sensor_id=measurement.sensor_id,
                        detail={"value": measurement.value, "quality": measurement.quality.value})


def from_anomaly(anomaly: AnomalyResult, *, cleared: bool = False) -> HealthEvent:
    event_type = HealthEventType.ANOMALY_CLEARED if cleared else HealthEventType.ANOMALY_DETECTED
    return HealthEvent(type=event_type, mono_ms=anomaly.mono_ms, sensor_id=anomaly.sensor_id,
                        detail={"severity": anomaly.severity.value, "kind": anomaly.kind, "reason": anomaly.reason})


def from_health_state_change(old_state: HealthState, new_state: HealthState, *, mono_ms: int) -> tuple[HealthEvent, ...]:
    """One state transition always yields HEALTH_STATE_CHANGED; entering WARNING or CRITICAL
    for the first time (not already in that state) also yields the matching dedicated event."""
    events = [HealthEvent(HealthEventType.HEALTH_STATE_CHANGED, mono_ms,
                           detail={"from": old_state.value, "to": new_state.value})]
    if new_state is HealthState.WARNING and old_state is not HealthState.WARNING:
        events.append(HealthEvent(HealthEventType.MACHINE_HEALTH_WARNING, mono_ms, detail={"state": new_state.value}))
    if new_state is HealthState.CRITICAL and old_state is not HealthState.CRITICAL:
        events.append(HealthEvent(HealthEventType.MACHINE_HEALTH_CRITICAL, mono_ms, detail={"state": new_state.value}))
    return tuple(events)


def from_health_score_change(old_score: HealthScore, new_score: HealthScore, *, mono_ms: int) -> HealthEvent:
    return HealthEvent(HealthEventType.HEALTH_SCORE_CHANGED, mono_ms,
                        detail={"from": old_score.value, "to": new_score.value})
