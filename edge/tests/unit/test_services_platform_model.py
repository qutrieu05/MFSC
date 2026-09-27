"""P6.1: unit tests for the platform domain model."""

from __future__ import annotations

import pytest

from msfc.core.errors import OrchestrationError
from msfc.domain import MachineState
from msfc.services import CellIdentity, CellSnapshot, PipelineOutcome, ProductCycleTrace, RuntimeState, SubsystemHealth


def test_cell_identity_rejects_empty_fields() -> None:
    with pytest.raises(OrchestrationError):
        CellIdentity(cell_id="", cell_device_id="esp32-cc01", edge_device_id="edge01", line_id="line01")
    with pytest.raises(OrchestrationError):
        CellIdentity(cell_id="cell01", cell_device_id="", edge_device_id="edge01", line_id="line01")


def test_cell_identity_accepts_valid_fields() -> None:
    identity = CellIdentity(cell_id="cell01", cell_device_id="esp32-cc01", edge_device_id="edge01", line_id="line01")
    assert identity.cell_id == "cell01"


def test_runtime_state_has_exactly_seven_values() -> None:
    assert {s.value for s in RuntimeState} == {
        "INIT", "READY", "RUNNING", "DEGRADED", "FAULT", "SAFE_STOP", "SHUTDOWN",
    }


def test_pipeline_outcome_reuses_verdict_vocabulary() -> None:
    assert PipelineOutcome.GOOD.value == "GOOD"
    assert PipelineOutcome.DEFECT.value == "DEFECT"


def test_product_cycle_trace_safety_denied_requires_reason() -> None:
    with pytest.raises(OrchestrationError):
        ProductCycleTrace(
            product_id="1-0", outcome=PipelineOutcome.SAFETY_DENIED,
            detected_at_mono_ms=0, decided_at_mono_ms=0,
        )


def test_product_cycle_trace_safety_denied_cannot_carry_a_decision() -> None:
    from msfc.domain import DecisionRecord, Verdict

    record = DecisionRecord(
        decision_id="d-1-0", product_id="1-0", final_verdict=Verdict.GOOD,
        reason_codes=("ALL_CHANNELS_GOOD",), rules_version="rules-0.1", late=False,
    )
    with pytest.raises(OrchestrationError):
        ProductCycleTrace(
            product_id="1-0", outcome=PipelineOutcome.SAFETY_DENIED,
            detected_at_mono_ms=0, decided_at_mono_ms=0, denial_reason="CELL_STATE_UNKNOWN",
            decision=record,
        )


def test_product_cycle_trace_good_outcome_is_constructible() -> None:
    trace = ProductCycleTrace(
        product_id="1-0", outcome=PipelineOutcome.GOOD, detected_at_mono_ms=0, decided_at_mono_ms=40,
    )
    assert trace.outcome is PipelineOutcome.GOOD
    assert trace.sorted_event is None


def test_subsystem_health_requires_matching_lengths() -> None:
    with pytest.raises(OrchestrationError):
        SubsystemHealth(degraded=("vision",), reasons=())


def test_subsystem_health_is_healthy_when_empty() -> None:
    assert SubsystemHealth().is_healthy is True
    assert SubsystemHealth(degraded=("vision",), reasons=("x",)).is_healthy is False


def test_cell_snapshot_aggregates_with_defaults() -> None:
    identity = CellIdentity(cell_id="cell01", cell_device_id="esp32-cc01", edge_device_id="edge01", line_id="line01")
    snapshot = CellSnapshot(identity=identity, runtime_state=RuntimeState.INIT, mono_ms=0)
    assert snapshot.machine_state is None
    assert snapshot.subsystems.is_healthy
    assert snapshot.active_fault_codes == ()


def test_cell_snapshot_can_report_a_running_machine() -> None:
    identity = CellIdentity(cell_id="cell01", cell_device_id="esp32-cc01", edge_device_id="edge01", line_id="line01")
    snapshot = CellSnapshot(
        identity=identity, runtime_state=RuntimeState.RUNNING, mono_ms=1000,
        machine_state=MachineState.RUNNING,
    )
    assert snapshot.machine_state is MachineState.RUNNING
