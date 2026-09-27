"""P6.4/P6.5: safety-gate tests.

Reminder encoded in every test here: this gate is a courtesy check, not the safety authority
(msfc/services/safety_gate.py's own docstring). These tests only prove the gate's own logic,
not that it is what keeps the cell safe -- that is msfc.sim.SimCellController's job, proven
separately in tests/integration/test_sim_cell_controller.py (unmodified) and again in
tests/integration/test_services_full_stack_integration.py.
"""

from __future__ import annotations

from msfc.domain import CellStateSnapshot, MachineState
from msfc.services.safety_gate import evaluate_safety_gate


def _state(machine_state: MachineState) -> CellStateSnapshot:
    return CellStateSnapshot(machine_state=machine_state)


def test_unknown_cell_state_is_denied_fail_closed() -> None:
    result = evaluate_safety_gate(None)
    assert result.allowed is False
    assert result.reason == "CELL_STATE_UNKNOWN"


def test_idle_is_allowed() -> None:
    result = evaluate_safety_gate(_state(MachineState.IDLE))
    assert result.allowed is True
    assert result.reason is None


def test_running_is_allowed() -> None:
    assert evaluate_safety_gate(_state(MachineState.RUNNING)).allowed is True


def test_estop_is_denied() -> None:
    result = evaluate_safety_gate(_state(MachineState.ESTOP))
    assert result.allowed is False
    assert result.reason == "CELL_LATCHED_ESTOP"


def test_fault_is_denied() -> None:
    result = evaluate_safety_gate(_state(MachineState.FAULT))
    assert result.allowed is False
    assert result.reason == "CELL_LATCHED_FAULT"


def test_safe_stop_is_denied() -> None:
    result = evaluate_safety_gate(_state(MachineState.SAFE_STOP))
    assert result.allowed is False
    assert result.reason == "CELL_LATCHED_SAFE_STOP"


def test_boot_and_self_test_are_allowed_not_latched() -> None:
    # BOOT/SELF_TEST are non-production but not latched -- a product can't physically arrive
    # then, but the gate itself should only ever deny for latched/unknown states (P6.4 scope).
    assert evaluate_safety_gate(_state(MachineState.BOOT)).allowed is True
    assert evaluate_safety_gate(_state(MachineState.SELF_TEST)).allowed is True
