"""P6.3: the top-level Cell Runtime -- lifecycle, subscriptions, and the aggregate read model.

    init -> subscribe (state/fault/product events/ack) -> process products as they arrive
         -> observe OEE/health independently -> shutdown

This is deliberately NOT a second Cell Controller and NOT a second safety state machine (P6.3's
own warning). It never decides ``MachineState`` -- it only *observes* what the real/simulated
Cell Controller reports over the bus and reacts within the bounds P6.4 allows (deny/allow
originating a new verdict; never clear a latch, never force an actuator, never bypass a
rejection). Per the layer rules (ARCHITECTURE.md section 7.2), this module -- like every module
in ``msfc.services`` -- never imports ``msfc.sim``: it talks to the Cell Controller purely
through :class:`~msfc.comm.MessageBus` and the contract registry, which is what makes "swap the
simulator for real firmware" (P6.19) an actual, not just claimed, property of this code.

Shared-bus discipline: this class never calls ``bus.start()``/``bus.stop()`` -- those affect
every subscriber on the bus (including a co-located ``SimCellController`` in tests), not just
this runtime. :meth:`shutdown` only stops *this* runtime from reacting further and releases its
own resources (the frame source).
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import replace

from msfc.analytics import (
    HealthEventType,
    MachineHealthMonitor,
    MachineMonitor,
    SensorSource,
    from_fault_report,
    from_product_detected,
    from_product_sorted,
    from_state_changed,
)
from msfc.comm import DedupeFilter, MessageBus
from msfc.contracts import ContractRegistry, PayloadValidator, SeqCounter, build_envelope
from msfc.core.errors import OrchestrationError
from msfc.core.logging_setup import ctx, get_logger
from msfc.decision import DecisionEngine
from msfc.domain import LATCHED_STATES, CellStateSnapshot, FaultSeverity, MachineState
from msfc.services import codec
from msfc.services.health_pipeline import bridge_critical_events, ingest_sensors
from msfc.services.pipeline import OcrStageConfig, VisionStageConfig, run_product_cycle
from msfc.services.platform_model import (
    CellIdentity,
    CellSnapshot,
    DashboardEvent,
    DashboardEventCategory,
    DashboardEventSeverity,
    PipelineOutcome,
    ProductCycleTrace,
    RuntimeState,
    SubsystemHealth,
)
from msfc.services.timing import StageTimer, TimingStats
from msfc.vision import Frame, FrameSource

log = get_logger("msfc.services.runtime")

_STATE_TOPIC = "conveyor.state"
_FAULT_TOPIC = "conveyor.fault"
_PRODUCT_DETECTED_TOPIC = "conveyor.event.product_detected"
_PRODUCT_SORTED_TOPIC = "conveyor.event.product_sorted"
_STATE_CHANGED_TOPIC = "conveyor.event.state_changed"
_ACK_TOPIC = "conveyor.ack"
_VERDICT_TOPIC = "conveyor.cmd.verdict"
_HEARTBEAT_TOPIC = "system.heartbeat"

_FAULT_SEVERITY_TO_EVENT_SEVERITY: dict[FaultSeverity, DashboardEventSeverity] = {
    FaultSeverity.INFO: DashboardEventSeverity.INFO,
    FaultSeverity.WARNING: DashboardEventSeverity.WARNING,
    FaultSeverity.FAULT: DashboardEventSeverity.FAULT,
    FaultSeverity.SAFETY: DashboardEventSeverity.CRITICAL,
}

_HEALTH_EVENT_SEVERITY: dict[HealthEventType, DashboardEventSeverity] = {
    HealthEventType.SENSOR_READING: DashboardEventSeverity.INFO,
    HealthEventType.ANOMALY_DETECTED: DashboardEventSeverity.WARNING,
    HealthEventType.ANOMALY_CLEARED: DashboardEventSeverity.INFO,
    HealthEventType.HEALTH_STATE_CHANGED: DashboardEventSeverity.INFO,
    HealthEventType.HEALTH_SCORE_CHANGED: DashboardEventSeverity.INFO,
    HealthEventType.SENSOR_FAULT: DashboardEventSeverity.WARNING,
    HealthEventType.MACHINE_HEALTH_WARNING: DashboardEventSeverity.WARNING,
    HealthEventType.MACHINE_HEALTH_CRITICAL: DashboardEventSeverity.CRITICAL,
}

_PIPELINE_OUTCOME_SEVERITY: dict[PipelineOutcome, DashboardEventSeverity] = {
    PipelineOutcome.GOOD: DashboardEventSeverity.INFO,
    PipelineOutcome.DEFECT: DashboardEventSeverity.WARNING,
    PipelineOutcome.SAFETY_DENIED: DashboardEventSeverity.WARNING,
    PipelineOutcome.NO_DECISION: DashboardEventSeverity.WARNING,
}


class CellRuntime:
    def __init__(
        self,
        *,
        identity: CellIdentity,
        bus: MessageBus,
        registry: ContractRegistry,
        decision_engine: DecisionEngine,
        vision: VisionStageConfig | None = None,
        frame_source: FrameSource | None = None,
        ocr: OcrStageConfig | None = None,
        machine_monitor: MachineMonitor | None = None,
        health_monitor: MachineHealthMonitor | None = None,
        sensors: list[SensorSource] | None = None,
        bridge_health_critical_to_oee: bool = False,
        decision_latency_ms: int = 0,
        fault_threshold: int = 3,
        product_history_size: int = 200,
        event_log_size: int = 300,
    ) -> None:
        if fault_threshold < 1:
            raise OrchestrationError(f"fault_threshold must be >= 1, got {fault_threshold!r}")
        if decision_latency_ms < 0:
            raise OrchestrationError(f"decision_latency_ms must be >= 0, got {decision_latency_ms!r}")
        self._identity = identity
        self._bus = bus
        self._registry = registry
        self._validator = PayloadValidator(registry)
        self._decision_engine = decision_engine
        self._vision = vision
        self._frame_source = frame_source
        self._ocr = ocr
        self._machine_monitor = machine_monitor
        self._health_monitor = health_monitor
        self._sensors = list(sensors) if sensors else []
        self._bridge_health_critical_to_oee = bridge_health_critical_to_oee
        self._decision_latency_ms = decision_latency_ms
        self._fault_threshold = fault_threshold

        self._seq = SeqCounter()
        self._started = False
        self._shutdown = False
        self._last_cell_state: CellStateSnapshot | None = None
        self._active_fault_codes: set[str] = set()
        self._degraded: dict[str, str] = {}
        self._consecutive_failures: dict[str, int] = {}
        self._pending_products: dict[str, ProductCycleTrace] = {}
        self._last_product: ProductCycleTrace | None = None
        self._last_mono_ms = 0
        self._timing_stats = TimingStats()

        # Dashboard-phase observability additions (additive, see DECISIONS.md): a bounded
        # product history (for a "production" page) and a bounded event log (for an "events"
        # page) -- both purely observational, fed only from data this runtime already computes
        # in its existing handlers, never a new decision input.
        self._product_history_size = product_history_size
        self._product_history: "OrderedDict[str, ProductCycleTrace]" = OrderedDict()
        self._event_log: "deque[DashboardEvent]" = deque(maxlen=event_log_size)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        """Subscribe to every Cell Controller topic this runtime needs. Idempotent."""
        if self._started:
            return
        fmt = self._registry.format_topic
        device_id = self._identity.cell_device_id
        line_id = self._identity.line_id
        self._bus.subscribe(fmt(_STATE_TOPIC, device_id=device_id, line_id=line_id), DedupeFilter(self._on_state))
        self._bus.subscribe(fmt(_FAULT_TOPIC, device_id=device_id, line_id=line_id), DedupeFilter(self._on_fault))
        self._bus.subscribe(fmt(_PRODUCT_DETECTED_TOPIC, device_id=device_id, line_id=line_id),
                             DedupeFilter(self._on_product_detected))
        self._bus.subscribe(fmt(_PRODUCT_SORTED_TOPIC, device_id=device_id, line_id=line_id),
                             DedupeFilter(self._on_product_sorted))
        self._bus.subscribe(fmt(_STATE_CHANGED_TOPIC, device_id=device_id, line_id=line_id),
                             DedupeFilter(self._on_state_changed))
        self._bus.subscribe(fmt(_ACK_TOPIC, device_id=device_id, line_id=line_id), DedupeFilter(self._on_ack))
        self._started = True
        log.info("cell runtime started", extra=ctx(cell_id=self._identity.cell_id, device_id=device_id))

    def shutdown(self) -> None:
        """Stop reacting to further messages and release owned resources. Sticky; does not
        touch the shared bus (other subscribers, e.g. a co-located simulator, are unaffected)."""
        if self._shutdown:
            return
        self._shutdown = True
        if self._frame_source is not None:
            self._frame_source.close()
        log.info("cell runtime shut down", extra=ctx(cell_id=self._identity.cell_id))

    def send_heartbeat(self, *, now_mono_ms: int, uptime_ms: int) -> None:
        """Publish this runtime's own edge heartbeat (SF-02). ``services_ok`` reflects
        whether this runtime itself considers itself healthy (not FAULT/SHUTDOWN) -- it is
        deliberately independent of the *cell's* MachineState, which the cell reports itself."""
        services_ok = self.runtime_state not in (RuntimeState.FAULT, RuntimeState.SHUTDOWN)
        self._publish(_HEARTBEAT_TOPIC, codec.edge_heartbeat_data(uptime_ms=uptime_ms, services_ok=services_ok),
                       mono_ms=now_mono_ms, device_id=self._identity.edge_device_id)

    # ------------------------------------------------------------------ read model
    @property
    def runtime_state(self) -> RuntimeState:
        if self._shutdown:
            return RuntimeState.SHUTDOWN
        if self._last_cell_state is None:
            return RuntimeState.INIT
        if self._last_cell_state.machine_state in LATCHED_STATES:
            return RuntimeState.SAFE_STOP
        if any(count >= self._fault_threshold for count in self._consecutive_failures.values()):
            return RuntimeState.FAULT
        if self._degraded:
            return RuntimeState.DEGRADED
        if self._last_cell_state.machine_state == MachineState.RUNNING:
            return RuntimeState.RUNNING
        return RuntimeState.READY

    @property
    def timing_stats(self) -> TimingStats:
        return self._timing_stats

    @property
    def ocr(self) -> OcrStageConfig | None:
        return self._ocr

    @ocr.setter
    def ocr(self, value: OcrStageConfig | None) -> None:
        """Additive, dashboard-phase capability: lets a caller (e.g. a demo control simulating
        an OCR outage) swap the OCR stage configuration between cycles without reconstructing
        the whole runtime. Does not change any existing behavior -- the constructor-supplied
        value is still used until this is called."""
        self._ocr = value

    @property
    def vision(self) -> VisionStageConfig | None:
        return self._vision

    @vision.setter
    def vision(self, value: VisionStageConfig | None) -> None:
        self._vision = value

    def product_history(self, *, limit: int | None = None) -> tuple[ProductCycleTrace, ...]:
        """Most-recent-last. Bounded to ``product_history_size`` entries (default 200)."""
        items = tuple(self._product_history.values())
        return items[-limit:] if limit is not None else items

    def event_log(self, *, limit: int | None = None) -> tuple[DashboardEvent, ...]:
        """Most-recent-last. Bounded to ``event_log_size`` entries (default 300)."""
        items = tuple(self._event_log)
        return items[-limit:] if limit is not None else items

    def snapshot(self, *, mono_ms: int) -> CellSnapshot:
        return CellSnapshot(
            identity=self._identity, runtime_state=self.runtime_state, mono_ms=mono_ms,
            machine_state=self._last_cell_state.machine_state if self._last_cell_state else None,
            cell_state=self._last_cell_state,
            subsystems=SubsystemHealth(degraded=tuple(self._degraded), reasons=tuple(self._degraded.values())),
            last_product=self._last_product,
            active_fault_codes=tuple(sorted(self._active_fault_codes)),
        )

    # ------------------------------------------------------------------ health/sensor tick (caller-driven; not event-based, matches P5's polled sensor model)
    def process_sensors(self, *, mono_ms: int) -> None:
        if self._shutdown or self._health_monitor is None or not self._sensors:
            return
        events, failed = ingest_sensors(self._sensors, self._health_monitor, mono_ms=mono_ms)
        if failed:
            self._mark_failed("health", f"sensors_unavailable:{','.join(failed)}", mono_ms=mono_ms)
        else:
            self._mark_recovered("health", mono_ms=mono_ms)
        for health_event in events:
            self._log_event(mono_ms=health_event.mono_ms, category=DashboardEventCategory.HEALTH,
                             severity=_HEALTH_EVENT_SEVERITY.get(health_event.type, DashboardEventSeverity.INFO),
                             message=f"{health_event.type.value} ({health_event.sensor_id or 'n/a'})")
        if self._bridge_health_critical_to_oee and self._machine_monitor is not None:
            for machine_event in bridge_critical_events(events):
                self._machine_monitor.apply(machine_event)

    # ------------------------------------------------------------------ bus handlers
    def _on_state(self, topic: str, envelope: dict) -> None:
        if self._shutdown:
            return
        try:
            self._validator.validate_for_topic(_STATE_TOPIC, envelope)
            cell_state = codec.decode_cell_state(envelope["data"])
        except Exception as exc:
            log.warning("dropped invalid cell state", extra=ctx(topic=topic, error=str(exc)))
            return
        self._last_cell_state = cell_state
        self._last_mono_ms = max(self._last_mono_ms, envelope.get("mono_ms", 0))

    def _on_fault(self, topic: str, envelope: dict) -> None:
        if self._shutdown:
            return
        try:
            self._validator.validate_for_topic(_FAULT_TOPIC, envelope)
            report = codec.decode_fault(envelope["data"])
        except Exception as exc:
            log.warning("dropped invalid fault report", extra=ctx(topic=topic, error=str(exc)))
            return
        if report.event == "RAISED":
            self._active_fault_codes.add(report.fault.code)
        else:
            self._active_fault_codes.discard(report.fault.code)
        if self._machine_monitor is not None:
            self._machine_monitor.apply(from_fault_report(report, mono_ms=envelope["mono_ms"]))
        self._log_event(
            mono_ms=envelope["mono_ms"], category=DashboardEventCategory.FAULT,
            severity=_FAULT_SEVERITY_TO_EVENT_SEVERITY[report.fault.severity],
            message=f"{report.fault.code} {report.fault.name} {report.event}",
        )

    def _on_state_changed(self, topic: str, envelope: dict) -> None:
        if self._shutdown:
            return
        try:
            self._validator.validate_for_topic(_STATE_CHANGED_TOPIC, envelope)
            event = codec.decode_state_changed(envelope["data"])
        except Exception as exc:
            log.warning("dropped invalid state_changed event", extra=ctx(topic=topic, error=str(exc)))
            return
        if self._machine_monitor is not None:
            self._machine_monitor.apply_many(from_state_changed(event, mono_ms=envelope["mono_ms"]))
        severity = (DashboardEventSeverity.CRITICAL if event.to_state is MachineState.ESTOP
                    else DashboardEventSeverity.WARNING if event.to_state in LATCHED_STATES
                    else DashboardEventSeverity.INFO)
        self._log_event(mono_ms=envelope["mono_ms"], category=DashboardEventCategory.STATE, severity=severity,
                         message=f"{event.from_state.value} -> {event.to_state.value} ({event.cause})")

    def _on_ack(self, topic: str, envelope: dict) -> None:
        if self._shutdown:
            return
        try:
            self._validator.validate_for_topic(_ACK_TOPIC, envelope)
            codec.decode_cmd_ack(envelope["data"])
        except Exception as exc:
            log.warning("dropped invalid command ack", extra=ctx(topic=topic, error=str(exc)))

    def _on_product_detected(self, topic: str, envelope: dict) -> None:
        if self._shutdown:
            return
        try:
            self._validator.validate_for_topic(_PRODUCT_DETECTED_TOPIC, envelope)
            event = codec.decode_product_detected(envelope["data"])
        except Exception as exc:
            log.warning("dropped invalid product_detected event", extra=ctx(topic=topic, error=str(exc)))
            return
        if self._machine_monitor is not None:
            self._machine_monitor.apply(from_product_detected(event))

        frame: Frame | None = None
        if self._frame_source is not None:
            try:
                frame = self._frame_source.read()
            except Exception as exc:
                log.warning("frame source unavailable this cycle", extra=ctx(product_id=event.product_id, error=str(exc)))
                self._mark_failed("frame_source", str(exc), mono_ms=event.t_detect_mono_ms)
        elif self._vision is not None or self._ocr is not None:
            self._mark_recovered("frame_source", mono_ms=event.t_detect_mono_ms)

        now_mono_ms = event.t_detect_mono_ms + self._decision_latency_ms
        timer = StageTimer(event.product_id)
        trace, failed = run_product_cycle(
            event.product_id, frame=frame, cell_state=self._last_cell_state,
            vision=self._vision, ocr=self._ocr, decision_engine=self._decision_engine,
            detected_at_mono_ms=event.t_detect_mono_ms, now_mono_ms=now_mono_ms, timer=timer,
        )
        self._timing_stats.record(timer.finish())
        self._update_channel_health(failed, mono_ms=now_mono_ms)
        self._pending_products[event.product_id] = trace
        self._last_product = trace
        self._record_product_history(trace)
        self._log_event(mono_ms=now_mono_ms, category=DashboardEventCategory.PRODUCT,
                         severity=_PIPELINE_OUTCOME_SEVERITY[trace.outcome],
                         message=f"product {event.product_id}: {trace.outcome.value}"
                                 + (f" ({trace.denial_reason})" if trace.denial_reason else ""),
                         product_id=event.product_id)

        if trace.verdict_command is not None:
            self._publish(_VERDICT_TOPIC, codec.verdict_command_data(trace.verdict_command), mono_ms=now_mono_ms,
                          device_id=self._identity.cell_device_id)

    def _on_product_sorted(self, topic: str, envelope: dict) -> None:
        if self._shutdown:
            return
        try:
            self._validator.validate_for_topic(_PRODUCT_SORTED_TOPIC, envelope)
            event = codec.decode_product_sorted(envelope["data"])
        except Exception as exc:
            log.warning("dropped invalid product_sorted event", extra=ctx(topic=topic, error=str(exc)))
            return
        if self._machine_monitor is not None:
            self._machine_monitor.apply_many(from_product_sorted(event))

        trace = self._pending_products.pop(event.product_id, None)
        if trace is not None:
            trace = replace(trace, sorted_event=event)
            self._last_product = trace
            self._record_product_history(trace)
        self._log_event(mono_ms=envelope["mono_ms"], category=DashboardEventCategory.PRODUCT,
                         severity=(DashboardEventSeverity.INFO if event.action.value == "PASSED"
                                   else DashboardEventSeverity.WARNING),
                         message=f"product {event.product_id} sorted: {event.action.value} ({event.reason.value})",
                         product_id=event.product_id)

    # ------------------------------------------------------------------ internals
    def _update_channel_health(self, failed_subsystems: tuple[str, ...], *, mono_ms: int) -> None:
        for name, configured in (("vision", self._vision is not None), ("ocr", self._ocr is not None)):
            if not configured:
                continue
            if name in failed_subsystems:
                self._mark_failed(name, "pipeline_error", mono_ms=mono_ms)
            else:
                self._mark_recovered(name, mono_ms=mono_ms)

    def _mark_failed(self, subsystem: str, reason: str, *, mono_ms: int) -> None:
        was_healthy = subsystem not in self._degraded
        self._degraded[subsystem] = reason
        self._consecutive_failures[subsystem] = self._consecutive_failures.get(subsystem, 0) + 1
        if was_healthy:
            self._log_event(mono_ms=mono_ms, category=DashboardEventCategory.RUNTIME,
                             severity=DashboardEventSeverity.WARNING,
                             message=f"subsystem '{subsystem}' degraded: {reason}")

    def _mark_recovered(self, subsystem: str, *, mono_ms: int) -> None:
        was_degraded = subsystem in self._degraded
        self._degraded.pop(subsystem, None)
        self._consecutive_failures[subsystem] = 0
        if was_degraded:
            self._log_event(mono_ms=mono_ms, category=DashboardEventCategory.RUNTIME,
                             severity=DashboardEventSeverity.INFO, message=f"subsystem '{subsystem}' recovered")

    def _log_event(self, *, mono_ms: int, category: DashboardEventCategory, severity: DashboardEventSeverity,
                    message: str, product_id: str | None = None) -> None:
        self._event_log.append(DashboardEvent(mono_ms=mono_ms, category=category, severity=severity,
                                               message=message, product_id=product_id))

    def _record_product_history(self, trace: ProductCycleTrace) -> None:
        self._product_history[trace.product_id] = trace
        self._product_history.move_to_end(trace.product_id)
        while len(self._product_history) > self._product_history_size:
            self._product_history.popitem(last=False)

    def _publish(self, topic_key: str, data: dict, *, mono_ms: int, device_id: str) -> None:
        spec = self._registry.topic(topic_key)
        envelope = build_envelope(schema=spec.schema, device_id=device_id,
                                   seq=self._seq.next(), mono_ms=mono_ms, data=data)
        self._validator.validate_for_topic(topic_key, envelope)  # never publish something we would reject
        topic = self._registry.format_topic(topic_key, device_id=device_id, line_id=self._identity.line_id)
        self._bus.publish(topic, envelope, qos=spec.qos, retain=spec.retain)


__all__ = ["CellRuntime"]
