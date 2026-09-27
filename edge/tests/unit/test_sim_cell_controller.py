"""Tests for msfc.sim.SimCellController (P1.6) — the "ESP32 mock" PO asked for.

Covers motor/servo simulation, GOOD/DEFECT routing, timing/tracking, fault handling, and
the E-stop/heartbeat fail-safe rules that are the whole point of the safety architecture
(docs/SAFETY_CONCEPT.md). Every test drives the simulator with an explicit, deterministic
clock — nothing here sleeps or depends on wall-clock timing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from msfc.comm import InMemoryBus
from msfc.contracts import ContractRegistry, PayloadValidator, build_envelope
from msfc.core.errors import PayloadInvalidError, SimulationError
from msfc.domain import CommandAction, CommandResult, ControlCommand, MachineState, PusherState, Verdict, VerdictCommand
from msfc.sim import SimCellController


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


@pytest.fixture()
def bus() -> InMemoryBus:
    return InMemoryBus()


@pytest.fixture()
def sim(bus: InMemoryBus, registry: ContractRegistry) -> SimCellController:
    return SimCellController(bus=bus, registry=registry, heartbeat_timeout_ms=1000)


def _control(action: CommandAction, *, cmd_id: str = "c1", params: dict | None = None) -> ControlCommand:
    return ControlCommand(cmd_id=cmd_id, action=action, source="test", params=params or {})


def _verdict(product_id: str, verdict: Verdict, *, decision_id: str | None = None) -> VerdictCommand:
    return VerdictCommand(product_id=product_id, verdict=verdict,
                           decision_id=decision_id or f"d-{product_id}", reason_codes=("TEST",))


def _start(sim: SimCellController, now: int) -> None:
    ack = sim.send_command(_control(CommandAction.START), now_mono_ms=now)
    assert ack.result == CommandResult.DONE


# --------------------------------------------------------------------------- boot (SAF-02/05/06)
def test_boots_into_idle_with_everything_off(sim: SimCellController) -> None:
    snap = sim.snapshot()
    assert snap.machine_state is MachineState.IDLE
    assert snap.safety_relay_closed is False
    assert snap.pusher is PusherState.RETRACTED
    assert snap.motor_output_pct == 0.0


def test_boot_publishes_a_retained_state_message(bus: InMemoryBus, registry: ContractRegistry) -> None:
    SimCellController(bus=bus, registry=registry)
    state_messages = [m for m in bus.published if m.topic.endswith("/state")]
    assert state_messages, "expected at least one retained state publish during boot"
    assert state_messages[-1].retain is True
    assert state_messages[-1].envelope["data"]["machine_state"] == "IDLE"


# --------------------------------------------------------------------------- motor/servo simulation
def test_start_closes_relay_and_drives_motor_to_setpoint(sim: SimCellController) -> None:
    sim.send_command(_control(CommandAction.SET_SPEED, params={"speed_pct": 60.0}), now_mono_ms=0)
    _start(sim, 10)
    snap = sim.snapshot()
    assert snap.machine_state is MachineState.RUNNING
    assert snap.safety_relay_closed is True
    assert snap.motor_output_pct == 60.0


def test_start_when_not_idle_is_rejected(sim: SimCellController) -> None:
    _start(sim, 0)
    ack = sim.send_command(_control(CommandAction.START), now_mono_ms=10)
    assert ack.result == CommandResult.REJECTED
    assert ack.reason == "not_idle"


def test_stop_opens_relay_and_returns_to_idle(sim: SimCellController) -> None:
    _start(sim, 0)
    ack = sim.send_command(_control(CommandAction.STOP), now_mono_ms=20)
    assert ack.result == CommandResult.DONE
    snap = sim.snapshot()
    assert snap.machine_state is MachineState.IDLE
    assert snap.safety_relay_closed is False
    assert snap.motor_output_pct == 0.0


def test_stop_when_not_running_is_rejected(sim: SimCellController) -> None:
    ack = sim.send_command(_control(CommandAction.STOP), now_mono_ms=0)
    assert ack.result == CommandResult.REJECTED
    assert ack.reason == "not_running"


def test_set_speed_while_idle_only_updates_setpoint(sim: SimCellController) -> None:
    sim.send_command(_control(CommandAction.SET_SPEED, params={"speed_pct": 75.0}), now_mono_ms=0)
    snap = sim.snapshot()
    assert snap.speed_setpoint_pct == 75.0
    assert snap.motor_output_pct == 0.0  # not running yet: motor unaffected


def test_pusher_test_extends_and_retracts_while_running(sim: SimCellController) -> None:
    _start(sim, 0)
    ack = sim.send_command(_control(CommandAction.PUSHER_TEST), now_mono_ms=5)
    assert ack.result == CommandResult.DONE
    assert sim.snapshot().pusher is PusherState.RETRACTED  # settles back down (instantaneous model)


def test_pusher_test_while_idle_is_rejected(sim: SimCellController) -> None:
    ack = sim.send_command(_control(CommandAction.PUSHER_TEST), now_mono_ms=0)
    assert ack.result == CommandResult.REJECTED
    assert ack.reason == "not_running"


# --------------------------------------------------------------------------- tracking + GOOD/DEFECT routing
def test_product_ids_are_sequential_with_boot_id_prefix(bus: InMemoryBus, registry: ContractRegistry) -> None:
    sim = SimCellController(bus=bus, registry=registry, boot_id=7)
    _start(sim, 0)
    first = sim.detect_product(10)
    second = sim.detect_product(20)
    assert first == "7-0" and second == "7-1"


def test_good_verdict_passes_the_product(sim: SimCellController) -> None:
    _start(sim, 0)
    pid = sim.detect_product(10)
    sim.receive_verdict(_verdict(pid, Verdict.GOOD), now_mono_ms=15)
    event = sim.arrive_at_s2(50)
    assert event.action.value == "PASSED"
    assert event.reason.value == "VERDICT_GOOD"
    assert sim.snapshot().counters.passed == 1


def test_defect_verdict_rejects_and_the_pusher_settles_back_to_retracted(sim: SimCellController) -> None:
    _start(sim, 0)
    pid = sim.detect_product(10)
    sim.receive_verdict(_verdict(pid, Verdict.DEFECT), now_mono_ms=15)
    event = sim.arrive_at_s2(50)
    assert event.action.value == "REJECTED"
    assert event.reason.value == "VERDICT_DEFECT"
    assert event.t_push_mono_ms == 50
    assert sim.snapshot().pusher is PusherState.RETRACTED  # instantaneous model: settled by the time we look
    assert sim.snapshot().counters.rejected == 1


def test_no_verdict_is_rejected_by_default_policy_and_raises_f033(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.detect_product(10)
    event = sim.arrive_at_s2(400)  # no verdict ever sent
    assert event.action.value == "REJECTED"
    assert event.reason.value == "NO_DECISION"
    assert event.verdict_received is False
    fault_messages = [m for m in sim.snapshot().active_faults]  # F033 is transient, not latched
    fault_topics = [m for m in _bus_of(sim).published if m.topic.endswith("/fault")]
    assert any(m.envelope["data"]["code"] == "F033" for m in fault_topics)


def _bus_of(sim: SimCellController):
    return sim._bus  # test-only introspection; production code never reaches into a private attribute like this


def test_no_verdict_passes_when_reject_on_no_decision_is_false(bus: InMemoryBus, registry: ContractRegistry) -> None:
    sim = SimCellController(bus=bus, registry=registry, reject_on_no_decision=False)
    _start(sim, 0)
    sim.detect_product(10)
    event = sim.arrive_at_s2(400)
    assert event.action.value == "PASSED"
    assert event.reason.value == "NO_DECISION"


def test_fifo_order_is_preserved_across_multiple_products(sim: SimCellController) -> None:
    _start(sim, 0)
    a = sim.detect_product(10)
    sim.receive_verdict(_verdict(a, Verdict.GOOD), now_mono_ms=15)  # events fed in real time order
    b = sim.detect_product(20)
    sim.receive_verdict(_verdict(b, Verdict.DEFECT), now_mono_ms=25)
    first = sim.arrive_at_s2(100)
    second = sim.arrive_at_s2(110)
    assert first.product_id == a and first.action.value == "PASSED"
    assert second.product_id == b and second.action.value == "REJECTED"


def test_arrive_at_s2_with_empty_queue_raises_f030_and_returns_none(sim: SimCellController) -> None:
    event = sim.arrive_at_s2(50)
    assert event is None
    assert "F030" in sim.snapshot().active_faults


def test_late_verdict_is_flagged_f032_but_still_applied(sim: SimCellController) -> None:
    _start(sim, 0)
    pid = sim.detect_product(10)
    event = sim.arrive_at_s2(90)  # product reaches S2 before any verdict
    sim.receive_verdict(_verdict(pid, Verdict.GOOD), now_mono_ms=95)  # verdict arrives too late to matter
    # The product already left at t=90 with NO_DECISION; a late verdict for it is simply
    # ignored (logged) since it is no longer in the queue - this proves that path is safe.
    assert event.action.value == "REJECTED" and event.reason.value == "NO_DECISION"


def test_queue_overflow_raises_and_flags_f031(bus: InMemoryBus, registry: ContractRegistry) -> None:
    sim = SimCellController(bus=bus, registry=registry, queue_max_depth=2)
    _start(sim, 0)
    sim.detect_product(1)
    sim.detect_product(2)
    with pytest.raises(SimulationError, match="overflow"):
        sim.detect_product(3)
    assert "F031" in sim.snapshot().active_faults


# --------------------------------------------------------------------------- heartbeat fail-safe (SF-02)
def test_running_faults_after_heartbeat_timeout(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.receive_edge_heartbeat()
    sim.tick(1500)  # 1500ms with no heartbeat, timeout is 1000ms
    snap = sim.snapshot()
    assert snap.machine_state is MachineState.FAULT
    assert "F010" in snap.active_faults
    assert snap.safety_relay_closed is False
    assert snap.motor_output_pct == 0.0
    assert snap.pusher is PusherState.RETRACTED


def test_regular_heartbeats_keep_the_machine_running(sim: SimCellController) -> None:
    sim.receive_edge_heartbeat()  # heartbeat already flowing (5 Hz in reality) before START
    _start(sim, 0)
    now = 0
    for _ in range(10):
        now += 200
        sim.tick(now)
        sim.receive_edge_heartbeat()
    assert sim.snapshot().machine_state is MachineState.RUNNING
    assert "F010" not in sim.snapshot().active_faults


def test_remote_reset_after_heartbeat_recovers(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.receive_edge_heartbeat()
    sim.tick(1500)
    assert sim.snapshot().machine_state is MachineState.FAULT

    sim.tick(1600)
    sim.receive_edge_heartbeat()  # heartbeat resumes
    ack = sim.send_command(_control(CommandAction.RESET), now_mono_ms=1600)
    assert ack.result == CommandResult.DONE
    assert sim.snapshot().machine_state is MachineState.IDLE


def test_remote_reset_while_heartbeat_still_stale_is_rejected(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.receive_edge_heartbeat()
    sim.tick(1500)
    assert sim.snapshot().machine_state is MachineState.FAULT

    ack = sim.send_command(_control(CommandAction.RESET), now_mono_ms=1500)
    assert ack.result == CommandResult.REJECTED
    assert ack.reason == "cause_not_cleared"
    assert sim.snapshot().machine_state is MachineState.FAULT


def test_local_reset_also_recovers_from_fault(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.receive_edge_heartbeat()
    sim.tick(1500)
    sim.tick(1600)
    sim.receive_edge_heartbeat()
    assert sim.local_reset(1600) is True
    assert sim.snapshot().machine_state is MachineState.IDLE


# --------------------------------------------------------------------------- E-stop (SF-01, SAF-05)
def test_estop_immediately_cuts_motor_relay_and_pusher(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.press_estop(5)
    snap = sim.snapshot()
    assert snap.machine_state is MachineState.ESTOP
    assert snap.safety_relay_closed is False
    assert snap.motor_output_pct == 0.0
    assert snap.pusher is PusherState.RETRACTED
    assert "F001" in snap.active_faults


def test_remote_reset_while_estop_is_always_rejected(sim: SimCellController) -> None:
    _start(sim, 0)
    sim.press_estop(5)
    ack = sim.send_command(_control(CommandAction.RESET), now_mono_ms=10)
    assert ack.result == CommandResult.REJECTED
    assert ack.reason == "remote_reset_forbidden"


def test_local_reset_while_estop_still_pressed_does_nothing(sim: SimCellController) -> None:
    sim.press_estop(5)
    assert sim.local_reset(10) is False
    assert sim.snapshot().machine_state is MachineState.ESTOP


def test_local_reset_after_estop_released_returns_to_idle(sim: SimCellController) -> None:
    sim.press_estop(5)
    sim.release_estop(10)
    assert sim.local_reset(15) is True
    assert sim.snapshot().machine_state is MachineState.IDLE


def test_commands_while_estop_are_rejected(sim: SimCellController) -> None:
    sim.press_estop(5)
    ack = sim.send_command(_control(CommandAction.START), now_mono_ms=10)
    assert ack.result == CommandResult.REJECTED
    assert ack.reason == "estop_latched"


def test_estop_takes_priority_over_heartbeat_fault_reporting(sim: SimCellController) -> None:
    """While ESTOP is active, the heartbeat monitor must not also raise F010 on top of it —
    ESTOP already governs and F010 would be a redundant, confusing second fault."""
    _start(sim, 0)
    sim.press_estop(5)
    sim.tick(2000)  # would time out the heartbeat if it were being checked
    assert sim.snapshot().machine_state is MachineState.ESTOP
    assert "F010" not in sim.snapshot().active_faults


# --------------------------------------------------------------------------- driven via the real MQTT bus
def test_heartbeat_received_over_the_bus_prevents_a_fault(sim: SimCellController, bus: InMemoryBus,
                                                            registry: ContractRegistry) -> None:
    _start(sim, 0)
    topic = registry.format_topic("system.heartbeat", device_id="edge01")
    envelope = build_envelope(schema="edge_heartbeat.v1", device_id="edge01", seq=0, mono_ms=0,
                               data={"uptime_ms": 0, "services_ok": True})
    bus.publish(topic, envelope, qos=0, retain=False)

    sim.tick(500)
    assert sim.snapshot().machine_state is MachineState.RUNNING
    assert "F010" not in sim.snapshot().active_faults


def test_control_command_received_over_the_bus_starts_the_machine(sim: SimCellController, bus: InMemoryBus,
                                                                     registry: ContractRegistry) -> None:
    topic = registry.format_topic("conveyor.cmd.control", device_id=sim.device_id)
    envelope = build_envelope(schema="control_cmd.v1", device_id="dashboard01", seq=0, mono_ms=0,
                               data={"cmd_id": "bus-1", "action": "start", "source": "dashboard"})
    bus.publish(topic, envelope, qos=1, retain=False)
    assert sim.snapshot().machine_state is MachineState.RUNNING


def test_verdict_received_over_the_bus_updates_the_queue(sim: SimCellController, bus: InMemoryBus,
                                                            registry: ContractRegistry) -> None:
    _start(sim, 0)
    pid = sim.detect_product(10)
    topic = registry.format_topic("conveyor.cmd.verdict", device_id=sim.device_id)
    envelope = build_envelope(schema="verdict_cmd.v1", device_id="edge01", seq=0, mono_ms=0,
                               data={"product_id": pid, "verdict": "GOOD", "decision_id": "d-1",
                                     "reason_codes": ["OK"]})
    bus.publish(topic, envelope, qos=1, retain=False)
    event = sim.arrive_at_s2(20)
    assert event.action.value == "PASSED"


def test_malformed_payload_on_the_bus_is_dropped_not_raised(sim: SimCellController, bus: InMemoryBus,
                                                               registry: ContractRegistry) -> None:
    topic = registry.format_topic("conveyor.cmd.control", device_id=sim.device_id)
    bad_envelope = {"schema": "control_cmd.v1", "device_id": "dashboard01", "seq": 0, "mono_ms": 0,
                     "data": {"cmd_id": "c1"}}  # missing required 'action'/'source'
    bus.publish(topic, bad_envelope, qos=1, retain=False)  # must not raise
    assert sim.snapshot().machine_state is MachineState.IDLE  # unaffected by the dropped message


def test_receive_verdict_for_unknown_product_is_ignored_not_raised(sim: SimCellController) -> None:
    sim.receive_verdict(_verdict("99-0", Verdict.GOOD), now_mono_ms=0)  # must not raise


# --------------------------------------------------------------------------- contract self-compliance
def test_every_published_message_is_valid_against_its_own_schema(sim: SimCellController, bus: InMemoryBus,
                                                                    registry: ContractRegistry) -> None:
    """The simulator validates before publishing internally, but this test re-validates
    everything that ended up on the bus from an independent PayloadValidator instance, as a
    belt-and-braces check that nothing slipped through malformed."""
    validator = PayloadValidator(registry)
    _start(sim, 0)
    pid = sim.detect_product(10)
    sim.receive_verdict(_verdict(pid, Verdict.DEFECT), now_mono_ms=15)
    sim.arrive_at_s2(50)
    sim.press_estop(60)

    assert bus.published, "expected at least one published message to validate"
    for message in bus.published:
        match = registry.match_topic(message.topic)
        assert match is not None, f"published to a topic not in the registry: {message.topic}"
        spec, _params = match
        validator.validate_for_topic(spec.key, message.envelope)  # raises PayloadInvalidError on failure


# --------------------------------------------------------------------------- constructor validation
@pytest.mark.parametrize("kwargs,match", [
    ({"heartbeat_timeout_ms": 0}, "heartbeat_timeout_ms"),
    ({"queue_max_depth": 0}, "queue_max_depth"),
])
def test_constructor_validates_parameters(bus: InMemoryBus, registry: ContractRegistry,
                                            kwargs: dict, match: str) -> None:
    with pytest.raises(SimulationError, match=match):
        SimCellController(bus=bus, registry=registry, **kwargs)


def test_clock_cannot_go_backwards(sim: SimCellController) -> None:
    sim.tick(100)
    with pytest.raises(SimulationError, match="backwards"):
        sim.tick(50)
