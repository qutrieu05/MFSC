"""P5.16/P5.17: the ONE, opt-in health-to-P4 bridge — not every anomaly becomes downtime."""

from __future__ import annotations

from msfc.analytics.events import MachineEventType
from msfc.analytics.health_models import HealthEvent, HealthEventType
from msfc.analytics.health_p4_bridge import bridge_critical_health_to_machine_event


def test_critical_health_event_becomes_a_fault_machine_event() -> None:
    health_event = HealthEvent(type=HealthEventType.MACHINE_HEALTH_CRITICAL, mono_ms=1000, sensor_id="temp01")
    machine_event = bridge_critical_health_to_machine_event(health_event)
    assert machine_event is not None
    assert machine_event.type is MachineEventType.FAULT
    assert machine_event.mono_ms == 1000
    assert machine_event.detail["source"] == "health"


def test_warning_health_event_does_not_bridge() -> None:
    """P5.17: 'warning without downtime' -- WARNING never produces a MachineEvent."""
    health_event = HealthEvent(type=HealthEventType.MACHINE_HEALTH_WARNING, mono_ms=1000)
    assert bridge_critical_health_to_machine_event(health_event) is None


def test_anomaly_detected_event_does_not_bridge() -> None:
    """P5.17: 'anomaly with continued production' -- ANOMALY_DETECTED never produces a
    MachineEvent through this bridge, only the dedicated MACHINE_HEALTH_CRITICAL does."""
    health_event = HealthEvent(type=HealthEventType.ANOMALY_DETECTED, mono_ms=1000)
    assert bridge_critical_health_to_machine_event(health_event) is None


def test_sensor_reading_event_does_not_bridge() -> None:
    health_event = HealthEvent(type=HealthEventType.SENSOR_READING, mono_ms=1000)
    assert bridge_critical_health_to_machine_event(health_event) is None


def test_health_state_changed_event_does_not_bridge() -> None:
    health_event = HealthEvent(type=HealthEventType.HEALTH_STATE_CHANGED, mono_ms=1000)
    assert bridge_critical_health_to_machine_event(health_event) is None
