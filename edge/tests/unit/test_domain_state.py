"""Tests for msfc.domain.state (CellStateSnapshot, Counters, FaultReport)."""

from __future__ import annotations

import pytest

from msfc.core.errors import DomainError
from msfc.domain import FAULT_CATALOG, CellStateSnapshot, Counters, FaultReport, MachineState, PusherState


# --------------------------------------------------------------------------- Counters
def test_counters_defaults_are_zero() -> None:
    c = Counters()
    assert (c.detected, c.passed, c.rejected, c.no_decision) == (0, 0, 0, 0)


def test_counters_with_detected_increments_only_detected() -> None:
    c = Counters().with_detected().with_detected()
    assert c.detected == 2 and c.passed == 0


def test_counters_with_passed_increments_only_passed() -> None:
    c = Counters().with_passed()
    assert c.passed == 1 and c.rejected == 0


def test_counters_with_rejected_no_decision_increments_both() -> None:
    c = Counters().with_rejected(no_decision=True)
    assert c.rejected == 1 and c.no_decision == 1


def test_counters_with_rejected_verdict_does_not_touch_no_decision() -> None:
    c = Counters().with_rejected(no_decision=False)
    assert c.rejected == 1 and c.no_decision == 0


def test_counters_are_immutable_originals_unchanged() -> None:
    base = Counters(detected=5)
    _ = base.with_detected()
    assert base.detected == 5  # replace() must not mutate the original


def test_counters_reject_negative_value() -> None:
    with pytest.raises(DomainError, match="detected"):
        Counters(detected=-1)


# --------------------------------------------------------------------------- CellStateSnapshot: SAF-10/SF-07
@pytest.mark.parametrize("state", [
    MachineState.BOOT, MachineState.SELF_TEST, MachineState.IDLE,
    MachineState.SAFE_STOP, MachineState.FAULT, MachineState.ESTOP,
])
def test_non_production_state_forbids_closed_relay(state: MachineState) -> None:
    """SAF-10: outside STARTING/RUNNING/STOPPING the safety relay must be open."""
    with pytest.raises(DomainError, match="SAF-10"):
        CellStateSnapshot(machine_state=state, safety_relay_closed=True)


@pytest.mark.parametrize("state", [
    MachineState.BOOT, MachineState.SELF_TEST, MachineState.IDLE,
    MachineState.SAFE_STOP, MachineState.FAULT, MachineState.ESTOP,
])
def test_non_production_state_forbids_extended_pusher(state: MachineState) -> None:
    """SF-07: outside STARTING/RUNNING/STOPPING the pusher must be retracted."""
    with pytest.raises(DomainError, match="SF-07"):
        CellStateSnapshot(machine_state=state, pusher=PusherState.EXTENDED)


@pytest.mark.parametrize("state", [MachineState.STARTING, MachineState.RUNNING, MachineState.STOPPING])
def test_production_states_allow_closed_relay_and_extended_pusher(state: MachineState) -> None:
    snap = CellStateSnapshot(machine_state=state, safety_relay_closed=True, pusher=PusherState.EXTENDED)
    assert snap.safety_relay_closed is True
    assert snap.pusher is PusherState.EXTENDED


def test_idle_snapshot_default_is_valid() -> None:
    snap = CellStateSnapshot(machine_state=MachineState.IDLE)
    assert snap.safety_relay_closed is False
    assert snap.pusher is PusherState.RETRACTED


@pytest.mark.parametrize("field,value", [("speed_setpoint_pct", 101.0), ("motor_output_pct", -1.0)])
def test_percentage_fields_are_range_checked(field: str, value: float) -> None:
    with pytest.raises(DomainError):
        CellStateSnapshot(machine_state=MachineState.RUNNING, safety_relay_closed=True, **{field: value})


def test_queue_len_rejects_negative() -> None:
    with pytest.raises(DomainError, match="queue_len"):
        CellStateSnapshot(machine_state=MachineState.IDLE, queue_len=-1)


def test_active_faults_round_trip_with_catalog() -> None:
    snap = CellStateSnapshot(machine_state=MachineState.FAULT, active_faults=("F010",))
    assert FAULT_CATALOG[snap.active_faults[0]].name == "COMM_LOSS_EDGE"


# --------------------------------------------------------------------------- FaultReport
def test_fault_report_happy_path() -> None:
    report = FaultReport(fault=FAULT_CATALOG["F010"], event="RAISED", detail="heartbeat missing 1200ms")
    assert report.fault.code == "F010"


def test_fault_report_rejects_bad_event() -> None:
    with pytest.raises(DomainError, match="event"):
        FaultReport(fault=FAULT_CATALOG["F010"], event="RESOLVED")


def test_fault_report_rejects_overlong_detail() -> None:
    with pytest.raises(DomainError, match="detail"):
        FaultReport(fault=FAULT_CATALOG["F010"], event="RAISED", detail="x" * 121)
