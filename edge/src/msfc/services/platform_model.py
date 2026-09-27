"""P6.1: the final software-level representation of one Edge AI cell.

Reuses P1-P5 models wherever a compatible concept already exists (the PO's explicit P6.1
rule): machine/safety state is still ``msfc.domain.enums.MachineState`` (there is no separate
"SafetyState" anywhere in this codebase -- safety is already the ``LATCHED_STATES`` subset of
``MachineState``, see ARCHITECTURE.md section 4 and msfc.domain.enums), vision/OCR results are
still ``msfc.domain.InspectionResult``, decisions are still ``msfc.domain.DecisionRecord``,
health is still ``msfc.analytics.MachineHealthSnapshot``, OEE is still
``msfc.analytics.MachineStatus``. The only genuinely new concepts below are the ones nothing
in P1-P5 already models: the orchestrator's own identity/lifecycle, and the two
orchestration-only outcomes (SAFETY_DENIED/NO_DECISION) that describe *why a verdict was never
attempted*, not what the verdict was.

Correlation: ``product_id`` (already the key threading ProductDetectedEvent -> InspectionResult
-> DecisionRecord -> VerdictCommand -> ProductSortedEvent since Phase 1) is reused as the one
correlation id for a product's trip through the platform. No new trace/correlation-id field is
introduced -- that would duplicate an existing, working concept and would require touching
frozen contracts for no benefit (P6.1: "avoid creating redundant domain models").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from msfc.core.errors import OrchestrationError
from msfc.domain import CellStateSnapshot, DecisionRecord, InspectionResult, MachineState, ProductSortedEvent, VerdictCommand


class RuntimeState(str, Enum):
    """P6.9: the Cell *Runtime's* (this Python orchestrator process) own lifecycle state --
    deliberately NOT a rename or a competitor of ``MachineState`` (the Cell Controller's own
    state, owned by firmware/``msfc.sim``) and NOT a new safety state machine. The runtime
    never commands a transition here; it only *reflects* what it has observed.

    INIT      -- constructed, not yet subscribed to anything.
    READY     -- subscribed and waiting; the cell is not currently RUNNING.
    RUNNING   -- the cell's own MachineState is RUNNING and the runtime is processing products.
    DEGRADED  -- a non-authoritative subsystem (vision/OCR/health/OEE) is failing, but the
                 runtime keeps operating on whatever channels remain (P6.11).
    FAULT     -- the runtime itself has an unrecoverable internal problem (repeated failures of
                 the same subsystem) -- distinct from the *cell's* FAULT state, which is
                 reported via ``machine_state`` instead.
    SAFE_STOP -- the cell's last known MachineState is latched (SAFE_STOP/FAULT/ESTOP); the
                 runtime has stopped originating new verdicts/commands. This mirrors, but never
                 causes or clears, the cell's own latch -- the cell's own safety logic is what
                 actually enforces it (P6.4).
    SHUTDOWN  -- stopped by an explicit shutdown() call; sticky.
    """

    INIT = "INIT"
    READY = "READY"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    SAFE_STOP = "SAFE_STOP"
    SHUTDOWN = "SHUTDOWN"


#: RuntimeStates in which the runtime must not originate a new verdict/control command.
NON_OPERATIONAL_RUNTIME_STATES = frozenset(
    {RuntimeState.INIT, RuntimeState.SAFE_STOP, RuntimeState.SHUTDOWN}
)


class PipelineOutcome(str, Enum):
    """The union of a real product :class:`~msfc.domain.enums.Verdict` (GOOD/DEFECT) plus the
    two orchestration-only "no verdict was even attempted" outcomes. SAFETY_DENIED/NO_DECISION
    describe an orchestration-layer decision *not* to decide, never a third kind of verdict
    sent to the Cell Controller (the wire contract, verdict_cmd.v1, is unchanged: still only
    GOOD/DEFECT, exactly as msfc.domain.enums.Verdict already restricts it)."""

    GOOD = "GOOD"
    DEFECT = "DEFECT"
    SAFETY_DENIED = "SAFETY_DENIED"
    NO_DECISION = "NO_DECISION"


@dataclass(frozen=True, slots=True)
class CellIdentity:
    """P6.1 "cell identity, runtime identity" -- two *different* device ids, deliberately kept
    separate rather than collapsed into one (a real mistake caught while wiring the heartbeat
    topic): ``cell_device_id`` is the Cell Controller (N1, real or simulated) this runtime
    orchestrates, used in every ``conveyor/{device_id}/...`` topic; ``edge_device_id`` is this
    Edge Server/runtime process's own identity, used only in ``system/{device_id}/...`` topics
    (``system.heartbeat`` etc. -- MQTT_CONTRACT.md: publisher "edge_server", a completely
    different device from the cell it is heartbeating to)."""

    cell_id: str
    cell_device_id: str
    edge_device_id: str
    line_id: str

    def __post_init__(self) -> None:
        for field_name in ("cell_id", "cell_device_id", "edge_device_id", "line_id"):
            if not getattr(self, field_name):
                raise OrchestrationError(f"CellIdentity.{field_name} must not be empty")


@dataclass(frozen=True, slots=True)
class ProductCycleTrace:
    """P6.8's traceable record of one product's trip through the platform, correlated by
    ``product_id``. A test can inspect this single object to see the whole chain: Input Frame
    (implied by whether ``inspection``/``label`` are present) -> Vision Result -> OCR Result ->
    Decision -> Command -> (once ``sorted_event`` arrives later) Controller Result."""

    product_id: str
    outcome: PipelineOutcome
    detected_at_mono_ms: int
    decided_at_mono_ms: int
    inspection: InspectionResult | None = None  # vision channel
    label: InspectionResult | None = None  # OCR channel (same domain type, model.backend="ocr")
    decision: DecisionRecord | None = None
    verdict_command: VerdictCommand | None = None
    denial_reason: str | None = None
    sorted_event: ProductSortedEvent | None = None  # filled in later, once product_sorted arrives

    def __post_init__(self) -> None:
        if self.outcome in (PipelineOutcome.SAFETY_DENIED, PipelineOutcome.NO_DECISION):
            if self.decision is not None or self.verdict_command is not None:
                raise OrchestrationError(
                    f"outcome={self.outcome.value} must not carry a decision/verdict_command"
                )
        if self.outcome == PipelineOutcome.SAFETY_DENIED and not self.denial_reason:
            raise OrchestrationError("SAFETY_DENIED requires a denial_reason")


@dataclass(frozen=True, slots=True)
class SubsystemHealth:
    """P6.10/P6.22: which non-authoritative subsystems are currently degraded, and why.
    Never includes the Cell Controller itself -- its state is ``machine_state``, authoritative,
    and never "degraded" (it is always exactly one MachineState)."""

    degraded: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.degraded) != len(self.reasons):
            raise OrchestrationError("degraded and reasons must have the same length")

    @property
    def is_healthy(self) -> bool:
        return not self.degraded


class DashboardEventCategory(str, Enum):
    """Which subsystem produced an event in :class:`DashboardEvent` -- the Dashboard phase's one
    justified, additive extension to :class:`~msfc.services.runtime.CellRuntime` (see
    DECISIONS.md): the runtime already sees every one of these events pass through its own
    handlers, so it is the correct place to keep a bounded observability log, rather than the
    dashboard reimplementing this tracking itself (which would duplicate business logic, exactly
    what the PO's dashboard directive forbids)."""

    STATE = "state"
    FAULT = "fault"
    PRODUCT = "product"
    HEALTH = "health"
    RUNTIME = "runtime"


class DashboardEventSeverity(str, Enum):
    """Deliberately reuses the same four bands already used elsewhere (FaultSeverity/
    AnomalySeverity) rather than inventing a fifth vocabulary."""

    INFO = "INFO"
    WARNING = "WARNING"
    FAULT = "FAULT"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class DashboardEvent:
    """One entry in :class:`~msfc.services.runtime.CellRuntime`'s bounded event log -- purely
    observational (P6.22/dashboard section 4.7), never a decision input for anything else."""

    mono_ms: int
    category: DashboardEventCategory
    severity: DashboardEventSeverity
    message: str
    product_id: str | None = None

    def __post_init__(self) -> None:
        if self.mono_ms < 0:
            raise OrchestrationError(f"mono_ms must be >= 0, got {self.mono_ms!r}")
        if not self.message:
            raise OrchestrationError("DashboardEvent.message must not be empty")


@dataclass(frozen=True, slots=True)
class CellSnapshot:
    """P6.1's aggregate read model: everything the platform currently knows about one cell, as
    of ``mono_ms`` (the Cell Controller's own clock, matching every other mono_ms in this
    codebase -- ARCHITECTURE.md section 5.1). Every field re-uses an existing P1-P5 type; this
    dataclass only adds the aggregation itself."""

    identity: CellIdentity
    runtime_state: RuntimeState
    mono_ms: int
    machine_state: MachineState | None = None  # None only before the first conveyor.state arrives
    cell_state: CellStateSnapshot | None = None
    subsystems: SubsystemHealth = field(default_factory=SubsystemHealth)
    last_product: ProductCycleTrace | None = None
    active_fault_codes: tuple[str, ...] = ()
