"""Cell Controller simulator (P1.6 "ESP32 firmware simulator/mock").

Speaks the *exact* MQTT contract a real ESP32 would (topics, envelopes, schemas) so that
once real firmware exists (P1.5/P1.10), swapping this simulator out changes nothing above
it — msfc.decision and msfc.vision have no idea whether they are talking to this class or
to real hardware (ARCHITECTURE.md's whole point of a HAL/simulator split, formalised in
docs/HARDWARE_INTERFACE.md section 5).

Scope and simplifications, stated up front rather than discovered by surprise later:

* **One clock, driven, never wall time.** ``self._now_mono_ms`` is the Cell Controller's own
  monotonic clock. Every public method that represents something happening takes
  ``now_mono_ms`` and advances this clock (never backwards). Critically, an *incoming*
  MQTT message's own ``mono_ms`` field is the **sender's** clock (the Edge Server's) and is
  never used as this device's time (ARCHITECTURE.md section 5.1: cross-device mono_ms
  values are not comparable) — call :meth:`tick` to advance this device's own clock and run
  the periodic safety checks a real firmware's control loop would run every cycle.
* Motor ramp and pusher extend/retract are modelled as instantaneous (no
  ``pusher.extend_ms``/motor ramp time yet — those are real numbers to calibrate in P1.11
  once hardware exists; see docs/HARDWARE_INTERFACE.md section 6).
* E-stop and the local RESET button are *physical* inputs (IF-HW-01/02) — modelled as direct
  method calls (:meth:`press_estop`, :meth:`release_estop`, :meth:`local_reset`), never as
  MQTT messages. A "remote reset" is what arrives via ``cmd/control`` with ``action=reset``.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from msfc.comm import MessageBus
from msfc.contracts import ContractRegistry, PayloadValidator, SeqCounter, build_envelope
from msfc.core.errors import PayloadInvalidError, SimulationError
from msfc.core.logging_setup import ctx, get_logger
from msfc.domain import (
    LATCHED_STATES,
    NON_PRODUCTION_STATES,
    CellStateSnapshot,
    CommandAck,
    CommandAction,
    CommandResult,
    ControlCommand,
    Counters,
    FaultReport,
    MachineState,
    ProductDetectedEvent,
    ProductSortedEvent,
    PusherState,
    RejectReason,
    SortAction,
    SortReason,
    StateChangedEvent,
    Verdict,
    VerdictCommand,
    lookup_fault,
)
from msfc.sim.codec import cell_state_data, fault_data, product_detected_data, product_sorted_data, state_changed_data

log = get_logger("msfc.sim")

_PRODUCTION_STATES = frozenset(MachineState) - NON_PRODUCTION_STATES


@dataclass(slots=True)
class _QueueEntry:
    detect_mono_ms: int
    verdict: VerdictCommand | None = None
    verdict_rx_mono_ms: int | None = None


class SimCellController:
    """A Cell Controller (N1) that exists only as MQTT messages on a :class:`MessageBus`."""

    def __init__(
        self,
        *,
        bus: MessageBus,
        registry: ContractRegistry,
        device_id: str = "esp32-cc01",
        line_id: str | None = None,
        boot_id: int = 1,
        heartbeat_timeout_ms: int = 1000,
        queue_max_depth: int = 8,
        reject_on_no_decision: bool = True,
    ) -> None:
        if heartbeat_timeout_ms <= 0:
            raise SimulationError(f"heartbeat_timeout_ms must be > 0, got {heartbeat_timeout_ms!r}")
        if queue_max_depth <= 0:
            raise SimulationError(f"queue_max_depth must be > 0, got {queue_max_depth!r}")

        self._bus = bus
        self._registry = registry
        self._validator = PayloadValidator(registry)
        self.device_id = device_id
        self.line_id = line_id or registry.default_line_id
        self._boot_id = boot_id
        self._seq = SeqCounter()
        self._heartbeat_timeout_ms = heartbeat_timeout_ms
        self._queue_max_depth = queue_max_depth
        self._reject_on_no_decision = reject_on_no_decision

        self._now_mono_ms = 0
        self._state = MachineState.BOOT
        self._faults: dict[str, bool] = {}  # code -> currently active
        self._counters = Counters()
        self._queue: "OrderedDict[str, _QueueEntry]" = OrderedDict()
        self._speed_setpoint_pct = 0.0
        self._motor_pct = 0.0
        self._relay_closed = False
        self._pusher = PusherState.RETRACTED
        self._detect_counter = 0
        self._last_edge_heartbeat_mono_ms: int | None = None
        self._estop_active = False

        self._bus.subscribe(
            registry.format_topic("system.heartbeat", device_id="+", line_id=self.line_id),
            self._on_edge_heartbeat,
        )
        self._bus.subscribe(
            registry.format_topic("conveyor.cmd.verdict", device_id=self.device_id, line_id=self.line_id),
            self._on_verdict_message,
        )
        self._bus.subscribe(
            registry.format_topic("conveyor.cmd.control", device_id=self.device_id, line_id=self.line_id),
            self._on_control_message,
        )

        self._boot()

    # ------------------------------------------------------------------ read-only view
    @property
    def state(self) -> MachineState:
        return self._state

    @property
    def now_mono_ms(self) -> int:
        return self._now_mono_ms

    @property
    def queue_len(self) -> int:
        return len(self._queue)

    def snapshot(self) -> CellStateSnapshot:
        return CellStateSnapshot(
            machine_state=self._state,
            active_faults=tuple(code for code, active in self._faults.items() if active),
            speed_setpoint_pct=self._speed_setpoint_pct,
            motor_output_pct=self._motor_pct,
            safety_relay_closed=self._relay_closed,
            pusher=self._pusher,
            queue_len=len(self._queue),
            safety_vision_required=False,  # Phase 2 feature; always False until then
            counters=self._counters,
        )

    def _advance_clock(self, now_mono_ms: int) -> None:
        if now_mono_ms < self._now_mono_ms:
            raise SimulationError(
                f"clock cannot go backwards: now_mono_ms={now_mono_ms} < current {self._now_mono_ms}"
            )
        self._now_mono_ms = now_mono_ms

    # ------------------------------------------------------------------ boot (SAF-02/05/06)
    def _boot(self) -> None:
        self._transition(MachineState.SELF_TEST, cause="boot")
        self._transition(MachineState.IDLE, cause="self_test_pass")
        self._publish_state()

    # ------------------------------------------------------------------ time passing (control loop)
    def tick(self, now_mono_ms: int) -> None:
        """Advance this device's own clock and run the periodic safety checks a real
        firmware's control loop runs every cycle (here: just the heartbeat monitor)."""
        self._advance_clock(now_mono_ms)
        self._check_heartbeat()

    # ------------------------------------------------------------------ physical inputs (IF-HW-01/02)
    def press_estop(self, now_mono_ms: int) -> None:
        """SAF-01: E-stop pressed — the hardware channel also cuts motor power directly;
        this call models the *software-visible* side (state, faults, telemetry)."""
        self._advance_clock(now_mono_ms)
        self._estop_active = True
        self._motor_pct = 0.0
        self._relay_closed = False
        self._pusher = PusherState.RETRACTED
        self._raise_fault("F001", detail="E-stop pressed")
        self._transition(MachineState.ESTOP, cause="F001")
        self._publish_state()

    def release_estop(self, now_mono_ms: int) -> None:
        """The button was released — this does *not* by itself leave ESTOP (SAF-05: a
        controlled, local reset is still required)."""
        self._advance_clock(now_mono_ms)
        self._estop_active = False
        self._clear_fault("F001")
        self._publish_state()

    def local_reset(self, now_mono_ms: int) -> bool:
        """RESET button pressed at the panel. Returns True if it cleared a latched state.

        SAF-05: ``ESTOP`` only clears once :meth:`release_estop` has already run (the button
        itself is no longer pressed) — this mirrors the real two-step "release then reset".
        """
        self._advance_clock(now_mono_ms)
        if self._state == MachineState.ESTOP:
            if self._estop_active:
                return False
            self._transition(MachineState.IDLE, cause="local_reset")
            self._publish_state()
            return True
        if self._state in (MachineState.FAULT, MachineState.SAFE_STOP):
            if not self._cause_cleared():
                return False
            self._clear_all_faults()
            self._transition(MachineState.IDLE, cause="local_reset")
            self._publish_state()
            return True
        return False  # nothing latched: no-op, not an error

    def _cause_cleared(self) -> bool:
        """Whether the condition that caused the current latch has gone away.

        Phase 1 only models one non-ESTOP cause: F010 (edge heartbeat loss). Phase 2 adds
        matching checks for the safety-vision faults (F020/F021).
        """
        if self._faults.get("F010"):
            return self._heartbeat_fresh()
        return True

    # ------------------------------------------------------------------ product tracking (ADR-0005)
    def detect_product(self, now_mono_ms: int, *, speed_setpoint_pct: float | None = None) -> str:
        """S1 fired: issue a ``product_id``, enqueue it, publish ``product_detected``."""
        self._advance_clock(now_mono_ms)
        if len(self._queue) >= self._queue_max_depth:
            self._raise_fault("F031", detail=f"queue depth {len(self._queue)} >= max {self._queue_max_depth}")
            raise SimulationError("product tracker queue overflow (F031)")

        product_id = f"{self._boot_id}-{self._detect_counter}"
        self._detect_counter += 1
        self._queue[product_id] = _QueueEntry(detect_mono_ms=now_mono_ms)
        self._counters = self._counters.with_detected()

        event = ProductDetectedEvent(product_id=product_id, t_detect_mono_ms=now_mono_ms,
                                      speed_setpoint_pct=speed_setpoint_pct)
        self._publish_event("conveyor.event.product_detected", product_detected_data(event))
        self._publish_state()
        return product_id

    def receive_verdict(self, cmd: VerdictCommand, *, now_mono_ms: int) -> None:
        """A :class:`VerdictCommand` arrived (normally via :meth:`_on_verdict_message`)."""
        self._advance_clock(now_mono_ms)
        entry = self._queue.get(cmd.product_id)
        if entry is None:
            log.warning("verdict for unknown/already-sorted product", extra=ctx(
                product_id=cmd.product_id, device_id=self.device_id
            ))
            return
        entry.verdict = cmd
        entry.verdict_rx_mono_ms = now_mono_ms

    def arrive_at_s2(self, now_mono_ms: int) -> ProductSortedEvent | None:
        """S2 fired: pop the oldest tracked product and decide PASSED/REJECTED.

        Returns ``None`` (and raises fault F030) if the queue is empty — a real sensor
        firing with nothing tracked means detection and sorting have desynchronised.
        """
        self._advance_clock(now_mono_ms)
        if not self._queue:
            self._raise_fault("F030", detail="S2 fired with an empty tracking queue")
            self._publish_state()
            return None

        product_id, entry = self._queue.popitem(last=False)
        action, reason, no_decision = self._route(entry)

        can_actuate = self._state in _PRODUCTION_STATES
        pushed = action == SortAction.REJECTED and can_actuate
        if pushed:
            self._pusher = PusherState.EXTENDED  # instantaneous in this MVP; see module docstring

        event = ProductSortedEvent(
            product_id=product_id, action=action, reason=reason,
            verdict_received=entry.verdict is not None,
            t_detect_mono_ms=entry.detect_mono_ms, t_s2_mono_ms=now_mono_ms,
            t_verdict_rx_mono_ms=entry.verdict_rx_mono_ms,
            t_push_mono_ms=now_mono_ms if pushed else None,
        )

        if action == SortAction.PASSED:
            self._counters = self._counters.with_passed()
        else:
            self._counters = self._counters.with_rejected(no_decision=no_decision)
            if no_decision:
                self._raise_transient_fault("F033", detail=f"product {product_id} rejected: no verdict in time")
        if event.margin_ms is not None and event.margin_ms <= 0:
            self._raise_transient_fault("F032", detail=f"product {product_id} verdict arrived after S2")

        self._publish_event("conveyor.event.product_sorted", product_sorted_data(event))
        if pushed:
            self._pusher = PusherState.RETRACTED  # see module docstring: no extend/retract timing modelled yet
        self._publish_state()
        return event

    def _route(self, entry: _QueueEntry) -> tuple[SortAction, SortReason, bool]:
        if entry.verdict is None:
            if self._reject_on_no_decision:
                return SortAction.REJECTED, SortReason.NO_DECISION, True
            return SortAction.PASSED, SortReason.NO_DECISION, True
        if entry.verdict.verdict == Verdict.GOOD:
            return SortAction.PASSED, SortReason.VERDICT_GOOD, False
        return SortAction.REJECTED, SortReason.VERDICT_DEFECT, False

    # ------------------------------------------------------------------ heartbeat monitor (SF-02)
    def receive_edge_heartbeat(self) -> None:
        """Record that an Edge Server heartbeat arrived *right now* (this device's clock).

        Deliberately takes no timestamp argument: the heartbeat message's own ``mono_ms`` is
        the sender's clock, not this device's — see the module docstring. Call :meth:`tick`
        first if time needs to advance before this arrival is recorded.
        """
        self._last_edge_heartbeat_mono_ms = self._now_mono_ms

    def _heartbeat_fresh(self) -> bool:
        if self._last_edge_heartbeat_mono_ms is None:
            return False
        return (self._now_mono_ms - self._last_edge_heartbeat_mono_ms) <= self._heartbeat_timeout_ms

    def _check_heartbeat(self) -> None:
        if self._estop_active or self._state == MachineState.ESTOP:
            return  # SF-01 already governs; do not also raise F010 on top of ESTOP
        if self._heartbeat_fresh():
            return
        if self._faults.get("F010"):
            return  # already latched
        self._motor_pct = 0.0
        self._relay_closed = False
        self._pusher = PusherState.RETRACTED
        self._raise_fault("F010", detail="edge heartbeat timeout")
        if self._state not in LATCHED_STATES:
            self._transition(MachineState.FAULT, cause="F010")
        self._publish_state()

    # ------------------------------------------------------------------ commands (MQTT_CONTRACT.md section 5)
    def send_command(self, cmd: ControlCommand, *, now_mono_ms: int) -> CommandAck:
        """Handle a :class:`ControlCommand` (normally via :meth:`_on_control_message`)."""
        self._advance_clock(now_mono_ms)

        if cmd.action == CommandAction.RESET:
            return self._handle_remote_reset(cmd)
        if self._estop_active or self._state == MachineState.ESTOP:
            return self._reject(cmd, RejectReason.ESTOP_LATCHED)
        if self._state == MachineState.FAULT:
            return self._reject(cmd, RejectReason.FAULT_LATCHED)
        if self._state == MachineState.SAFE_STOP:
            return self._reject(cmd, RejectReason.SAFE_STOP_LATCHED)

        if cmd.action == CommandAction.START:
            return self._handle_start(cmd)
        if cmd.action == CommandAction.STOP:
            return self._handle_stop(cmd)
        if cmd.action == CommandAction.SET_SPEED:
            return self._handle_set_speed(cmd)
        if cmd.action == CommandAction.PUSHER_TEST:
            return self._handle_pusher_test(cmd)
        raise SimulationError(f"unhandled command action {cmd.action!r}")  # pragma: no cover - exhaustive above

    def _handle_start(self, cmd: ControlCommand) -> CommandAck:
        if self._state != MachineState.IDLE:
            return self._reject(cmd, RejectReason.NOT_IDLE)
        self._transition(MachineState.STARTING, cause=f"cmd:{cmd.cmd_id}")
        self._relay_closed = True
        self._motor_pct = self._speed_setpoint_pct
        self._transition(MachineState.RUNNING, cause="ramp_complete")
        self._publish_state()
        return self._ack(cmd, CommandResult.DONE)

    def _handle_stop(self, cmd: ControlCommand) -> CommandAck:
        if self._state not in _PRODUCTION_STATES:
            return self._reject(cmd, RejectReason.NOT_RUNNING)
        self._transition(MachineState.STOPPING, cause=f"cmd:{cmd.cmd_id}")
        self._motor_pct = 0.0
        self._relay_closed = False
        self._pusher = PusherState.RETRACTED
        self._transition(MachineState.IDLE, cause="stop_complete")
        self._publish_state()
        return self._ack(cmd, CommandResult.DONE)

    def _handle_set_speed(self, cmd: ControlCommand) -> CommandAck:
        speed_pct = cmd.params["speed_pct"]  # ControlCommand.__post_init__ already required this
        self._speed_setpoint_pct = speed_pct
        if self._state in _PRODUCTION_STATES:
            self._motor_pct = speed_pct
        self._publish_state()
        return self._ack(cmd, CommandResult.DONE)

    def _handle_pusher_test(self, cmd: ControlCommand) -> CommandAck:
        if self._state not in _PRODUCTION_STATES:
            return self._reject(cmd, RejectReason.NOT_RUNNING)
        self._pusher = PusherState.EXTENDED
        self._publish_state()
        self._pusher = PusherState.RETRACTED
        self._publish_state()
        return self._ack(cmd, CommandResult.DONE)

    def _handle_remote_reset(self, cmd: ControlCommand) -> CommandAck:
        if self._state == MachineState.ESTOP:
            return self._reject(cmd, RejectReason.REMOTE_RESET_FORBIDDEN)
        if self._state in (MachineState.FAULT, MachineState.SAFE_STOP):
            if not self._cause_cleared():
                return self._reject(cmd, RejectReason.CAUSE_NOT_CLEARED)
            self._clear_all_faults()
            self._transition(MachineState.IDLE, cause="remote_reset")
            self._publish_state()
        return self._ack(cmd, CommandResult.DONE)  # nothing latched: idempotent no-op success

    def _ack(self, cmd: ControlCommand, result: CommandResult, *, reason: str | None = None) -> CommandAck:
        ack = CommandAck(cmd_id=cmd.cmd_id, action=cmd.action.value, result=result,
                          reason=reason, state_after=self._state)
        self._publish_event("conveyor.ack", {
            "cmd_id": ack.cmd_id, "action": ack.action, "result": ack.result.value,
            **({"reason": ack.reason} if ack.reason else {}),
            "state_after": ack.state_after.value if ack.state_after else None,
        })
        return ack

    def _reject(self, cmd: ControlCommand, reason: RejectReason) -> CommandAck:
        return self._ack(cmd, CommandResult.REJECTED, reason=reason.value)

    # ------------------------------------------------------------------ fault management (SAFETY_CONCEPT.md 5)
    def _raise_fault(self, code: str, *, detail: str = "") -> None:
        entry = lookup_fault(code)
        already = self._faults.get(code, False)
        self._faults[code] = True
        if not already:
            self._publish_event("conveyor.fault", fault_data(FaultReport(fault=entry, event="RAISED", detail=detail)))
            log.warning("fault raised", extra=ctx(code=code, name=entry.name, device_id=self.device_id))

    def _raise_transient_fault(self, code: str, *, detail: str = "") -> None:
        """A WARNING-severity fault that is reported once and does not stay 'active'
        (F032/F033: counted events, not a persistent condition to later clear)."""
        entry = lookup_fault(code)
        self._publish_event("conveyor.fault", fault_data(FaultReport(fault=entry, event="RAISED", detail=detail)))

    def _clear_fault(self, code: str) -> None:
        if self._faults.get(code):
            entry = lookup_fault(code)
            self._faults[code] = False
            self._publish_event("conveyor.fault", fault_data(FaultReport(fault=entry, event="CLEARED")))

    def _clear_all_faults(self) -> None:
        for code in [c for c, active in self._faults.items() if active]:
            self._clear_fault(code)

    # ------------------------------------------------------------------ MQTT boundary
    def _on_edge_heartbeat(self, topic: str, envelope: dict) -> None:
        try:
            self._validator.validate_for_topic("system.heartbeat", envelope)
        except PayloadInvalidError as exc:
            log.warning("dropped invalid heartbeat", extra=ctx(topic=topic, error=str(exc)))
            return
        self.receive_edge_heartbeat()

    def _on_verdict_message(self, topic: str, envelope: dict) -> None:
        try:
            self._validator.validate_for_topic("conveyor.cmd.verdict", envelope)
        except PayloadInvalidError as exc:
            log.warning("dropped invalid verdict", extra=ctx(topic=topic, error=str(exc)))
            return
        data = envelope["data"]
        cmd = VerdictCommand(product_id=data["product_id"], verdict=Verdict(data["verdict"]),
                              decision_id=data["decision_id"], reason_codes=tuple(data["reason_codes"]),
                              confidence=data.get("confidence"))
        self.receive_verdict(cmd, now_mono_ms=self._now_mono_ms)

    def _on_control_message(self, topic: str, envelope: dict) -> None:
        try:
            self._validator.validate_for_topic("conveyor.cmd.control", envelope)
        except PayloadInvalidError as exc:
            log.warning("dropped invalid control command", extra=ctx(topic=topic, error=str(exc)))
            return
        data = envelope["data"]
        cmd = ControlCommand(cmd_id=data["cmd_id"], action=CommandAction(data["action"]),
                              source=data["source"], params=data.get("params", {}))
        self.send_command(cmd, now_mono_ms=self._now_mono_ms)

    def _transition(self, to_state: MachineState, *, cause: str) -> None:
        from_state = self._state
        self._state = to_state
        event = StateChangedEvent(from_state=from_state, to_state=to_state, cause=cause)
        self._publish_event("conveyor.event.state_changed", state_changed_data(event))
        log.info("state transition", extra=ctx(device_id=self.device_id, **{"from": from_state.value},
                                                to=to_state.value, cause=cause))

    def _publish_state(self) -> None:
        self._publish("conveyor.state", cell_state_data(self.snapshot()))

    def _publish_event(self, topic_key: str, data: dict) -> None:
        self._publish(topic_key, data)

    def _publish(self, topic_key: str, data: dict) -> None:
        spec = self._registry.topic(topic_key)
        envelope = build_envelope(schema=spec.schema, device_id=self.device_id, boot_id=self._boot_id,
                                   seq=self._seq.next(), mono_ms=self._now_mono_ms, data=data)
        self._validator.validate_for_topic(topic_key, envelope)  # never publish something we would reject
        topic = self._registry.format_topic(topic_key, device_id=self.device_id, line_id=self.line_id)
        self._bus.publish(topic, envelope, qos=spec.qos, retain=spec.retain)
