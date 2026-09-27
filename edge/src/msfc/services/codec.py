"""Envelope ``data`` dict -> domain object, for the Cell Controller messages ``msfc.services``
consumes off the bus.

The mirror image of ``msfc.sim.codec`` (domain object -> dict), which ``msfc.services`` is not
allowed to import (the layer rules forbid ``services`` -> ``sim`` -- ARCHITECTURE.md section
7.2, enforced by test_layer_dependencies.py). This is exactly the point: a *real* Edge Server
receives Cell Controller state only as wire data, never as a live Python object handed to it by
the same process that made it, so this decode step is what a real deployment needs regardless
of whether the sender is ``SimCellController`` (today) or real firmware (P6.19: hardware
replacement). ``msfc.sim._on_verdict_message``/``_on_control_message`` already decode inline
for the one message type the simulator itself receives; this module does the same thing for
every message type ``services`` receives, kept together because there are five of them.
"""

from __future__ import annotations

from msfc.core.errors import OrchestrationError
from msfc.domain import (
    CellStateSnapshot,
    CommandAck,
    CommandResult,
    ControlCommand,
    Counters,
    FaultCode,
    FaultReport,
    MachineState,
    ProductDetectedEvent,
    ProductSortedEvent,
    PusherState,
    SortAction,
    SortReason,
    StateChangedEvent,
    VerdictCommand,
    lookup_fault,
)


def decode_cell_state(data: dict) -> CellStateSnapshot:
    counters = data["counters"]
    return CellStateSnapshot(
        machine_state=MachineState(data["machine_state"]),
        active_faults=tuple(data["active_faults"]),
        speed_setpoint_pct=data["speed_setpoint_pct"],
        motor_output_pct=data["motor_output_pct"],
        safety_relay_closed=data["safety_relay_closed"],
        pusher=PusherState(data["pusher"]),
        queue_len=data["queue_len"],
        safety_vision_required=data["safety_vision_required"],
        counters=Counters(
            detected=counters["detected"], passed=counters["passed"],
            rejected=counters["rejected"], no_decision=counters["no_decision"],
        ),
    )


def decode_state_changed(data: dict) -> StateChangedEvent:
    return StateChangedEvent(
        from_state=MachineState(data["from"]), to_state=MachineState(data["to"]), cause=data["cause"],
    )


def decode_fault(data: dict) -> FaultReport:
    fault: FaultCode = lookup_fault(data["code"])
    return FaultReport(fault=fault, event=data["event"], detail=data.get("detail", ""))


def decode_product_detected(data: dict) -> ProductDetectedEvent:
    return ProductDetectedEvent(
        product_id=data["product_id"],
        t_detect_mono_ms=data["t_detect_mono_ms"],
        sensor=data.get("sensor", "S1"),
        speed_setpoint_pct=data.get("speed_setpoint_pct"),
    )


def decode_product_sorted(data: dict) -> ProductSortedEvent:
    return ProductSortedEvent(
        product_id=data["product_id"],
        action=SortAction(data["action"]),
        reason=SortReason(data["reason"]),
        verdict_received=data["verdict_received"],
        t_detect_mono_ms=data["t_detect_mono_ms"],
        t_s2_mono_ms=data["t_s2_mono_ms"],
        t_verdict_rx_mono_ms=data.get("t_verdict_rx_mono_ms"),
        t_push_mono_ms=data.get("t_push_mono_ms"),
    )


def decode_cmd_ack(data: dict) -> CommandAck:
    state_after = data.get("state_after")
    return CommandAck(
        cmd_id=data["cmd_id"], action=data["action"], result=CommandResult(data["result"]),
        reason=data.get("reason"), state_after=MachineState(state_after) if state_after else None,
    )


def verdict_command_data(cmd: VerdictCommand) -> dict:
    """Encode a :class:`VerdictCommand` for publishing (verdict_cmd.v1) -- the mirror image of
    ``msfc.sim.engine._on_verdict_message``'s inline decode of the same schema."""
    data: dict = {
        "product_id": cmd.product_id, "verdict": cmd.verdict.value,
        "decision_id": cmd.decision_id, "reason_codes": list(cmd.reason_codes),
    }
    if cmd.confidence is not None:
        data["confidence"] = cmd.confidence
    return data


def control_command_data(cmd: ControlCommand) -> dict:
    """Encode a :class:`ControlCommand` for publishing (control_cmd.v1)."""
    data: dict = {"cmd_id": cmd.cmd_id, "action": cmd.action.value, "source": cmd.source}
    if cmd.params:
        data["params"] = dict(cmd.params)
    return data


def edge_heartbeat_data(*, uptime_ms: int, services_ok: bool) -> dict:
    """Encode the Edge Server's own heartbeat (edge_heartbeat.v1, SF-02: safety-relevant --
    its absence beyond ``comm.heartbeat_timeout_ms`` puts the Cell Controller into
    FAULT(COMM_LOSS), already implemented and tested in msfc.sim)."""
    return {"uptime_ms": uptime_ms, "services_ok": services_ok}


_DECODERS = {
    "cell_state.v1": decode_cell_state,
    "state_changed.v1": decode_state_changed,
    "fault.v1": decode_fault,
    "product_detected.v1": decode_product_detected,
    "product_sorted.v1": decode_product_sorted,
    "cmd_ack.v1": decode_cmd_ack,
}


def decode(schema: str, data: dict) -> object:
    """Dispatch by envelope ``schema`` name -- for a handler that subscribes to more than one
    topic and wants one entry point rather than re-checking the topic string."""
    try:
        decoder = _DECODERS[schema]
    except KeyError as exc:
        raise OrchestrationError(f"no decoder registered for schema {schema!r}") from exc
    return decoder(data)
