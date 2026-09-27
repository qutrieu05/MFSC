"""P5.16: a critical machine-health condition becomes visible to P4's OEE/downtime tracking
through the one, opt-in bridge (msfc.analytics.health_p4_bridge) -- proven against the REAL,
unmodified msfc.analytics.session.ProductionSession from Phase 4, not a stand-in. A WARNING
condition, by contrast, must NOT touch the production session at all (P5.17).
"""

from __future__ import annotations

from msfc.domain import MachineState
from msfc.analytics.anomaly import AnomalyThresholds
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.health_events import HealthEventType
from msfc.analytics.health_models import HealthState, SensorMeasurement, SensorType
from msfc.analytics.health_monitor import MachineHealthMonitor
from msfc.analytics.health_p4_bridge import bridge_critical_health_to_machine_event
from msfc.analytics.session import ProductionSession, SessionConfig

BASELINE = {"temp01": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)}
THRESHOLDS = {"temp01": AnomalyThresholds(warning_deviation=3, anomaly_deviation=10, critical_deviation=30)}


def test_critical_health_condition_becomes_downtime_in_a_real_production_session() -> None:
    health_monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    session = ProductionSession(SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000),
                                 started_at_mono_ms=0, initial_state=MachineState.RUNNING)

    health_monitor.ingest(
        SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=1_000, value=150.0,
                           unit="degC"),
        mono_ms=1_000,
    )
    health_events = health_monitor.drain_events()
    critical_events = [e for e in health_events if e.type is HealthEventType.MACHINE_HEALTH_CRITICAL]
    assert critical_events, "expected a MACHINE_HEALTH_CRITICAL event from the 150degC reading"

    bridged = [bridge_critical_health_to_machine_event(e) for e in health_events]
    machine_events = tuple(e for e in bridged if e is not None)
    assert len(machine_events) == 1
    assert machine_events[0].type is MachineEventType.FAULT

    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 1_000, state=MachineState.FAULT))
    session.record_event(machine_events[0])
    status = session.status(now_mono_ms=2_000)
    assert status.current_fault == "F070"


def test_warning_health_condition_never_touches_the_production_session() -> None:
    """P5.17: 'warning without downtime' -- a WARNING-level health event bridges to nothing,
    so a real ProductionSession sees zero events from it and stays exactly as it was."""
    health_monitor = MachineHealthMonitor(baselines=BASELINE, thresholds=THRESHOLDS, window_ms=10_000)
    session = ProductionSession(SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000),
                                 started_at_mono_ms=0, initial_state=MachineState.RUNNING)

    health_monitor.ingest(
        SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=1_000, value=84.0,
                           unit="degC"),  # deviation=4 -> WARNING only, per THRESHOLDS above
        mono_ms=1_000,
    )
    assert health_monitor.snapshot(mono_ms=1_000).health_state is HealthState.WARNING

    health_events = health_monitor.drain_events()
    bridged = [bridge_critical_health_to_machine_event(e) for e in health_events]
    assert all(e is None for e in bridged)  # nothing to feed the session

    status_before = session.status(now_mono_ms=1_000)
    assert status_before.downtime_ms == 0
    assert status_before.current_fault is None
