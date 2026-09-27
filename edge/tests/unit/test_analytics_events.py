"""P4.3 machine event abstraction, including its factory functions built from the existing,
unmodified msfc.domain events (StateChangedEvent, ProductDetectedEvent, ProductSortedEvent,
FaultReport) -- proving P4.16's "reuse compatible interfaces" without changing them.
"""

from __future__ import annotations

import pytest

from msfc.core.errors import OeeError
from msfc.domain import (
    FaultCode,
    FaultReport,
    FaultSeverity,
    MachineState,
    ProductDetectedEvent,
    ProductSortedEvent,
    SortAction,
    SortReason,
    StateChangedEvent,
)
from msfc.analytics.events import (
    MachineEvent,
    MachineEventType,
    from_fault_report,
    from_product_detected,
    from_product_sorted,
    from_state_changed,
)

_FAULT = FaultCode(code="F010", name="COMM_LOSS_EDGE", severity=FaultSeverity.FAULT, latching=True,
                    description="test fault")


def test_machine_event_rejects_negative_mono_ms() -> None:
    with pytest.raises(OeeError, match="mono_ms"):
        MachineEvent(MachineEventType.RESET, -1)


def test_machine_event_type_is_exactly_the_po_named_events() -> None:
    assert {t.value for t in MachineEventType} == {
        "machine_start", "machine_stop", "cycle_start", "cycle_complete", "product_good",
        "product_defect", "downtime_start", "downtime_end", "fault", "fault_clear",
        "emergency_stop", "reset",
    }


# --------------------------------------------------------------------------- from_state_changed
def test_idle_to_running_yields_machine_start_and_downtime_end() -> None:
    event = StateChangedEvent(from_state=MachineState.IDLE, to_state=MachineState.RUNNING, cause="start_cmd")
    derived = from_state_changed(event, mono_ms=1000)
    types = {e.type for e in derived}
    assert types == {MachineEventType.DOWNTIME_END, MachineEventType.MACHINE_START}
    assert all(e.state is MachineState.RUNNING for e in derived)


def test_running_to_idle_yields_machine_stop_and_downtime_start() -> None:
    event = StateChangedEvent(from_state=MachineState.RUNNING, to_state=MachineState.IDLE, cause="stop_cmd")
    derived = from_state_changed(event, mono_ms=2000)
    types = {e.type for e in derived}
    assert types == {MachineEventType.DOWNTIME_START, MachineEventType.MACHINE_STOP}


def test_running_to_estop_yields_emergency_stop_and_downtime_start() -> None:
    event = StateChangedEvent(from_state=MachineState.RUNNING, to_state=MachineState.ESTOP, cause="wire_cut")
    derived = from_state_changed(event, mono_ms=3000)
    types = {e.type for e in derived}
    assert types == {MachineEventType.EMERGENCY_STOP, MachineEventType.DOWNTIME_START, MachineEventType.MACHINE_STOP}


def test_estop_to_idle_yields_reset_and_downtime_end() -> None:
    event = StateChangedEvent(from_state=MachineState.ESTOP, to_state=MachineState.IDLE, cause="reset_cmd")
    derived = from_state_changed(event, mono_ms=4000)
    types = {e.type for e in derived}
    assert MachineEventType.RESET in types
    assert MachineEventType.DOWNTIME_END in types
    assert MachineEventType.EMERGENCY_STOP not in types  # only fires entering ESTOP, not leaving


def test_running_to_stopping_is_neither_downtime_nor_machine_stop() -> None:
    """STARTING/STOPPING are transitional run-time states (D-047) -- crossing into STOPPING
    from RUNNING is a machine_stop signal (motion is winding down) but not a downtime
    boundary, since STOPPING itself isn't in NON_PRODUCTION_STATES."""
    event = StateChangedEvent(from_state=MachineState.RUNNING, to_state=MachineState.STOPPING, cause="stop_cmd")
    derived = from_state_changed(event, mono_ms=5000)
    types = {e.type for e in derived}
    assert MachineEventType.DOWNTIME_START not in types
    assert MachineEventType.MACHINE_STOP in types


def test_fault_to_fault_produces_no_events() -> None:
    """A no-op-shaped transition (shouldn't normally occur, but must not crash or double-fire)."""
    event = StateChangedEvent(from_state=MachineState.FAULT, to_state=MachineState.FAULT, cause="noop")
    assert from_state_changed(event, mono_ms=1000) == ()


# --------------------------------------------------------------------------- from_product_detected/sorted
def test_from_product_detected_is_a_cycle_start() -> None:
    detected = ProductDetectedEvent(product_id="7-1", t_detect_mono_ms=1000)
    event = from_product_detected(detected)
    assert event.type is MachineEventType.CYCLE_START
    assert event.product_id == "7-1"
    assert event.mono_ms == 1000


def test_from_product_sorted_passed_yields_cycle_complete_and_product_good() -> None:
    sorted_event = ProductSortedEvent(
        product_id="7-1", action=SortAction.PASSED, reason=SortReason.VERDICT_GOOD,
        verdict_received=True, t_detect_mono_ms=1000, t_s2_mono_ms=1800, t_verdict_rx_mono_ms=1500,
    )
    complete, outcome = from_product_sorted(sorted_event)
    assert complete.type is MachineEventType.CYCLE_COMPLETE
    assert complete.detail["cycle_time_ms"] == 800
    assert outcome.type is MachineEventType.PRODUCT_GOOD
    assert outcome.mono_ms == 1800


def test_from_product_sorted_rejected_yields_product_defect() -> None:
    sorted_event = ProductSortedEvent(
        product_id="7-2", action=SortAction.REJECTED, reason=SortReason.VERDICT_DEFECT,
        verdict_received=True, t_detect_mono_ms=1000, t_s2_mono_ms=1800, t_verdict_rx_mono_ms=1500,
    )
    _complete, outcome = from_product_sorted(sorted_event)
    assert outcome.type is MachineEventType.PRODUCT_DEFECT
    assert outcome.detail["reason"] == "VERDICT_DEFECT"


def test_from_product_sorted_no_decision_is_still_product_defect() -> None:
    """D-045: a fail-closed NO_DECISION reject counts as a defect for OEE, same as an
    explicit VERDICT_DEFECT -- msfc.decision already made it REJECTED before this point."""
    sorted_event = ProductSortedEvent(
        product_id="7-3", action=SortAction.REJECTED, reason=SortReason.NO_DECISION,
        verdict_received=False, t_detect_mono_ms=1000, t_s2_mono_ms=1800,
    )
    _complete, outcome = from_product_sorted(sorted_event)
    assert outcome.type is MachineEventType.PRODUCT_DEFECT
    assert outcome.detail["reason"] == "NO_DECISION"


# --------------------------------------------------------------------------- from_fault_report
def test_from_fault_report_raised() -> None:
    report = FaultReport(fault=_FAULT, event="RAISED", detail="heartbeat timeout")
    event = from_fault_report(report, mono_ms=5000)
    assert event.type is MachineEventType.FAULT
    assert event.detail["fault_code"] == "F010"


def test_from_fault_report_cleared() -> None:
    report = FaultReport(fault=_FAULT, event="CLEARED")
    event = from_fault_report(report, mono_ms=6000)
    assert event.type is MachineEventType.FAULT_CLEAR
