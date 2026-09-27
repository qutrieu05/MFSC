"""P6.6: round-trip tests for msfc.services.codec against msfc.sim.codec's encoders.

Only test files may import msfc.sim (the layer rules forbid msfc.services from doing so --
see msfc/services/__init__.py's docstring); using it here to build known-good encoded
envelopes is exactly the "prove services can decode whatever the real/simulated Cell Controller
actually sends" property P6.19 depends on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from msfc.contracts import ContractRegistry, PayloadValidator, build_envelope
from msfc.domain import (
    CellStateSnapshot,
    CommandAck,
    CommandResult,
    ControlCommand,
    CommandAction,
    Counters,
    FaultReport,
    MachineState,
    ProductDetectedEvent,
    ProductSortedEvent,
    PusherState,
    SortAction,
    SortReason,
    StateChangedEvent,
    Verdict,
    VerdictCommand,
    lookup_fault,
)
from msfc.services import codec
from msfc.sim import codec as sim_codec


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


def test_decode_cell_state_round_trips(registry: ContractRegistry) -> None:
    snapshot = CellStateSnapshot(
        machine_state=MachineState.RUNNING, active_faults=("F032",), speed_setpoint_pct=50.0,
        motor_output_pct=50.0, safety_relay_closed=True, pusher=PusherState.RETRACTED,
        queue_len=2, safety_vision_required=False,
        counters=Counters(detected=5, passed=3, rejected=2, no_decision=1),
    )
    data = sim_codec.cell_state_data(snapshot)
    decoded = codec.decode_cell_state(data)
    assert decoded == snapshot


def test_decode_state_changed_round_trips() -> None:
    event = StateChangedEvent(from_state=MachineState.IDLE, to_state=MachineState.STARTING, cause="cmd:start-1")
    decoded = codec.decode_state_changed(sim_codec.state_changed_data(event))
    assert decoded == event


def test_decode_fault_round_trips() -> None:
    report = FaultReport(fault=lookup_fault("F010"), event="RAISED", detail="edge heartbeat timeout")
    decoded = codec.decode_fault(sim_codec.fault_data(report))
    assert decoded == report


def test_decode_product_detected_round_trips() -> None:
    event = ProductDetectedEvent(product_id="1-0", t_detect_mono_ms=1000, speed_setpoint_pct=50.0)
    decoded = codec.decode_product_detected(sim_codec.product_detected_data(event))
    assert decoded == event


def test_decode_product_sorted_round_trips() -> None:
    event = ProductSortedEvent(
        product_id="1-0", action=SortAction.REJECTED, reason=SortReason.VERDICT_DEFECT,
        verdict_received=True, t_detect_mono_ms=1000, t_s2_mono_ms=1500, t_verdict_rx_mono_ms=1040,
    )
    decoded = codec.decode_product_sorted(sim_codec.product_sorted_data(event))
    assert decoded == event


def test_decode_cmd_ack_round_trips() -> None:
    ack = CommandAck(cmd_id="start-1", action="start", result=CommandResult.DONE, state_after=MachineState.RUNNING)
    # cmd_ack is published inline by msfc.sim (no dedicated encoder) -- rebuild the same shape.
    data = {"cmd_id": ack.cmd_id, "action": ack.action, "result": ack.result.value, "state_after": ack.state_after.value}
    decoded = codec.decode_cmd_ack(data)
    assert decoded == ack


def test_decode_dispatches_by_schema_name() -> None:
    event = StateChangedEvent(from_state=MachineState.IDLE, to_state=MachineState.RUNNING, cause="x")
    data = sim_codec.state_changed_data(event)
    assert codec.decode("state_changed.v1", data) == event


def test_decode_unknown_schema_raises() -> None:
    from msfc.core.errors import OrchestrationError

    with pytest.raises(OrchestrationError):
        codec.decode("not_a_real_schema.v1", {})


def test_verdict_command_data_validates_against_schema(registry: ContractRegistry) -> None:
    cmd = VerdictCommand(product_id="1-0", verdict=Verdict.DEFECT, decision_id="d-1-0",
                          reason_codes=("ORACLE_DEFECT",), confidence=0.9)
    envelope = build_envelope(schema="verdict_cmd.v1", device_id="edge01", seq=0, mono_ms=0,
                               data=codec.verdict_command_data(cmd))
    PayloadValidator(registry).validate_for_topic("conveyor.cmd.verdict", envelope)


def test_control_command_data_validates_against_schema(registry: ContractRegistry) -> None:
    cmd = ControlCommand(cmd_id="start-1", action=CommandAction.START, source="services")
    envelope = build_envelope(schema="control_cmd.v1", device_id="edge01", seq=0, mono_ms=0,
                               data=codec.control_command_data(cmd))
    PayloadValidator(registry).validate_for_topic("conveyor.cmd.control", envelope)


def test_edge_heartbeat_data_validates_against_schema(registry: ContractRegistry) -> None:
    envelope = build_envelope(schema="edge_heartbeat.v1", device_id="edge01", seq=0, mono_ms=0,
                               data=codec.edge_heartbeat_data(uptime_ms=1000, services_ok=True))
    PayloadValidator(registry).validate_for_topic("system.heartbeat", envelope)
