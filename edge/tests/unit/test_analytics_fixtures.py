"""P4.13 deterministic simulation scenarios + P4.14's 15 named fixtures.

The 10 scenario_* functions in msfc.analytics.simulate cover P4.13's list directly; this file
runs each through a real ProductionSession and asserts the hand-computed expected numbers
(shown in each scenario's own docstring). The remaining P4.14 fixtures that aren't one of the
10 simulation scenarios (zero production, zero planned time, zero run time, invalid timestamp,
missing/incomplete sequence, multiple downtime intervals) are covered directly here.
"""

from __future__ import annotations

import pytest

from msfc.core.errors import OeeError
from msfc.domain import MachineState
from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.monitor import MachineMonitor
from msfc.analytics.session import ProductionSession, SessionConfig
from msfc.analytics import simulate as sim


def _run(config: SessionConfig, events: tuple[MachineEvent, ...], *, now_mono_ms: int | None = None):
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    for event in events:
        session.record_event(event)
    end = now_mono_ms if now_mono_ms is not None else (events[-1].mono_ms if events else 0)
    return session.status(now_mono_ms=max(end, 0))


# --------------------------------------------------------------------------- P4.13: 10 named scenarios
def test_scenario_1_normal_production() -> None:
    status = _run(*sim.scenario_normal_production())
    assert status.cycle_count == 10 and status.defect_count == 0
    assert status.oee.oee == pytest.approx(1.0)


def test_scenario_2_normal_cycles() -> None:
    status = _run(*sim.scenario_normal_cycles())
    assert status.oee.oee == pytest.approx(1.0)


def test_scenario_3_planned_downtime() -> None:
    status = _run(*sim.scenario_planned_downtime())
    assert status.oee.oee == pytest.approx(1.0)  # PLANNED excluded from the denominator (D-049)


def test_scenario_4_unplanned_downtime() -> None:
    status = _run(*sim.scenario_unplanned_downtime())
    assert status.oee.availability == pytest.approx(4_000 / 14_000)
    assert status.oee.performance == pytest.approx(1.0)


def test_scenario_5_machine_fault() -> None:
    status = _run(*sim.scenario_machine_fault())
    assert status.cycle_count == 0
    assert status.current_fault is None  # FAULT_CLEAR arrived before the end of the scenario


def test_scenario_6_emergency_stop() -> None:
    status = _run(*sim.scenario_emergency_stop())
    assert status.state is MachineState.IDLE  # reset back to IDLE by the end
    assert status.oee.availability == 0.0


def test_scenario_7_defect_production() -> None:
    status = _run(*sim.scenario_defect_production())
    assert status.oee.quality == 0.0
    assert status.oee.oee == 0.0


def test_scenario_8_mixed_good_defect_production() -> None:
    status = _run(*sim.scenario_mixed_good_defect_production())
    assert status.oee.quality == pytest.approx(5 / 8)


def test_scenario_9_slow_cycles() -> None:
    status = _run(*sim.scenario_slow_cycles())
    assert status.oee.performance == pytest.approx(0.5)
    assert status.cycle_stats.slow_cycle_count == 4


def test_scenario_10_multiple_production_sessions() -> None:
    results = []
    for config, events in sim.scenario_multiple_production_sessions():
        results.append(_run(config, events))
    assert results[0].good_count == 1 and results[0].defect_count == 0
    assert results[1].good_count == 0 and results[1].defect_count == 1
    assert results[0].session_name != results[1].session_name


# --------------------------------------------------------------------------- P4.14: remaining fixtures
def test_fixture_7_zero_production() -> None:
    """No events recorded at all -- a valid, deterministic zero-activity session."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000, name="zero_production")
    status = _run(config, (), now_mono_ms=10_000)
    assert status.cycle_count == 0
    assert status.oee.performance == 0.0
    assert status.oee.quality == 0.0


def test_fixture_8_zero_planned_production_time_is_rejected_at_construction() -> None:
    """SessionConfig itself refuses a zero/invalid planned time -- fails fast, deterministically."""
    with pytest.raises(OeeError, match="planned_production_time_ms"):
        SessionConfig(planned_production_time_ms=0, ideal_cycle_time_ms=1_000, name="zero_planned_time")


def test_fixture_9_zero_run_time_with_production_is_rejected_not_misleading() -> None:
    """Downtime spans the entire planned window (exactly matching planned_production_time_ms),
    yet a cycle was also recorded inside that same window -- contradictory input, and must
    fail loudly (P4.5: 'do not allow invalid data to silently produce misleading metrics'),
    not silently report some fake performance number."""
    config = SessionConfig(planned_production_time_ms=1_000, ideal_cycle_time_ms=1_000, name="zero_run_time")
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 0, state=MachineState.FAULT))
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"))
    session.record_event(MachineEvent(MachineEventType.CYCLE_COMPLETE, 500, product_id="7-1"))
    session.record_event(MachineEvent(MachineEventType.PRODUCT_GOOD, 500, product_id="7-1"))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 1_000, state=MachineState.RUNNING))
    with pytest.raises(OeeError, match="run_time_ms"):
        session.calculate_oee(now_mono_ms=1_000)


def test_fixture_10_invalid_negative_timestamp_is_rejected_at_construction() -> None:
    with pytest.raises(OeeError, match="mono_ms"):
        MachineEvent(MachineEventType.CYCLE_START, -100, product_id="7-1")


def test_fixture_14_missing_incomplete_event_sequence() -> None:
    """cycle_start with no cycle_complete by session end -- reported as still-open, not
    silently dropped or counted as finished."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000, name="incomplete_sequence")
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"))
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 1_000, product_id="7-2"))
    session.record_event(MachineEvent(MachineEventType.CYCLE_COMPLETE, 2_000, product_id="7-2"))
    session.record_event(MachineEvent(MachineEventType.PRODUCT_GOOD, 2_000, product_id="7-2"))
    stats = session.cycle_statistics()
    assert stats.count == 1  # only 7-2 completed
    # 7-1 is still open -- not counted as complete, not counted as incomplete either (it may
    # yet complete later); msfc.analytics never guesses at data it hasn't received.
    assert stats.incomplete_count == 0


def test_fixture_15_multiple_downtime_intervals() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000, name="multi_downtime")
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 0, state=MachineState.FAULT))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 500, state=MachineState.RUNNING))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 1_000, state=MachineState.ESTOP))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 1_800, state=MachineState.IDLE))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 2_000, state=MachineState.IDLE))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 2_200, state=MachineState.RUNNING))
    status = session.status(now_mono_ms=3_000)
    assert status.downtime_ms == 500 + 800 + 200


# --------------------------------------------------------------------------- MachineMonitor drives a scenario end to end
def test_machine_monitor_can_drive_a_full_scenario() -> None:
    config, events = sim.scenario_mixed_good_defect_production()
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    monitor = MachineMonitor(session)
    monitor.apply_many(events)
    status = monitor.status(now_mono_ms=events[-1].mono_ms)
    assert status.cycle_count == 8
    assert status.oee.quality == pytest.approx(5 / 8)
