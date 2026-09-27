"""P4.11 machine monitoring layer."""

from __future__ import annotations

from msfc.domain import MachineState
from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.monitor import MachineMonitor
from msfc.analytics.session import ProductionSession, SessionConfig

CONFIG = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)


def _session() -> ProductionSession:
    return ProductionSession(CONFIG, started_at_mono_ms=0, initial_state=MachineState.RUNNING)


def test_monitor_exposes_current_status() -> None:
    monitor = MachineMonitor(_session())
    monitor.apply(MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"))
    monitor.apply(MachineEvent(MachineEventType.CYCLE_COMPLETE, 1_000, product_id="7-1"))
    monitor.apply(MachineEvent(MachineEventType.PRODUCT_GOOD, 1_000, product_id="7-1"))

    status = monitor.status(now_mono_ms=1_000)
    assert status.cycle_count == 1
    assert status.good_count == 1
    assert status.last_event_type == "product_good"
    assert status.last_event_mono_ms == 1_000


def test_monitor_apply_many_processes_events_in_order() -> None:
    monitor = MachineMonitor(_session())
    events = (
        MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"),
        MachineEvent(MachineEventType.CYCLE_COMPLETE, 1_000, product_id="7-1"),
        MachineEvent(MachineEventType.PRODUCT_DEFECT, 1_000, product_id="7-1"),
    )
    monitor.apply_many(events)
    assert monitor.status(now_mono_ms=1_000).defect_count == 1


def test_monitor_oee_snapshot_matches_session_calculation() -> None:
    monitor = MachineMonitor(_session())
    monitor.apply_many((
        MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"),
        MachineEvent(MachineEventType.CYCLE_COMPLETE, 1_000, product_id="7-1"),
        MachineEvent(MachineEventType.PRODUCT_GOOD, 1_000, product_id="7-1"),
    ))
    snapshot = monitor.oee_snapshot(now_mono_ms=1_000)
    assert snapshot.total_count == 1
    assert snapshot.good_count == 1


def test_monitor_start_new_session_resets_accumulated_data() -> None:
    monitor = MachineMonitor(_session())
    monitor.apply(MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"))
    monitor.apply(MachineEvent(MachineEventType.CYCLE_COMPLETE, 1_000, product_id="7-1"))
    monitor.apply(MachineEvent(MachineEventType.PRODUCT_GOOD, 1_000, product_id="7-1"))
    assert monitor.status(now_mono_ms=1_000).cycle_count == 1

    new_config = SessionConfig(planned_production_time_ms=5_000, ideal_cycle_time_ms=500, name="shift-2")
    monitor.start_new_session(new_config, started_at_mono_ms=2_000, initial_state=MachineState.RUNNING)
    status = monitor.status(now_mono_ms=2_000)
    assert status.cycle_count == 0
    assert status.session_name == "shift-2"


def test_monitor_cycle_statistics_delegates_to_session() -> None:
    monitor = MachineMonitor(_session())
    monitor.apply_many((
        MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"),
        MachineEvent(MachineEventType.CYCLE_COMPLETE, 1_000, product_id="7-1"),
        MachineEvent(MachineEventType.PRODUCT_GOOD, 1_000, product_id="7-1"),
    ))
    stats = monitor.cycle_statistics()
    assert stats.count == 1
    assert stats.min_ms == 1_000
