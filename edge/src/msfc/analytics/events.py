"""Machine-event abstraction (P4.3).

Deliberately its own normalized type, not a rename of an existing msfc.domain event — nothing
in P1-P3 already unifies "product detected/sorted" and "state changed" into one stream shaped
for OEE's needs (cycle boundaries, downtime start/end, fault/fault_clear). The factory
functions below build ``MachineEvent``s FROM the existing, unmodified domain events
(``StateChangedEvent``, ``ProductDetectedEvent``, ``ProductSortedEvent``, ``FaultReport``) so
no upstream code changes (P4.16: "reuse compatible interfaces").

Every event carries an explicit ``mono_ms`` — always injected by the caller, never read from
the host clock (P4.3: "use an injectable clock/reference time for tests").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from msfc.core.errors import OeeError
from msfc.domain import (
    NON_PRODUCTION_STATES,
    FaultReport,
    MachineState,
    ProductDetectedEvent,
    ProductSortedEvent,
    SortAction,
    StateChangedEvent,
)
from msfc.analytics.models import DowntimeCategory


class MachineEventType(str, Enum):
    MACHINE_START = "machine_start"
    MACHINE_STOP = "machine_stop"
    CYCLE_START = "cycle_start"
    CYCLE_COMPLETE = "cycle_complete"
    PRODUCT_GOOD = "product_good"
    PRODUCT_DEFECT = "product_defect"
    DOWNTIME_START = "downtime_start"
    DOWNTIME_END = "downtime_end"
    FAULT = "fault"
    FAULT_CLEAR = "fault_clear"
    EMERGENCY_STOP = "emergency_stop"
    RESET = "reset"


@dataclass(frozen=True, slots=True)
class MachineEvent:
    type: MachineEventType
    mono_ms: int
    product_id: str | None = None
    state: MachineState | None = None  # the resulting MachineState, for state-derived events
    category: DowntimeCategory | None = None  # DOWNTIME_START only: explicit override of the
    # state-based default (msfc.analytics.session.DEFAULT_STATE_CATEGORY) -- the only way to
    # mark an interval PLANNED/MAINTENANCE, since no MachineState maps to those by default
    # (P4.4: a state alone can't say "this IDLE time was scheduled," only a human/scheduler can)
    detail: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mono_ms < 0:
            raise OeeError(f"mono_ms must be >= 0, got {self.mono_ms!r}")


def from_state_changed(event: StateChangedEvent, *, mono_ms: int) -> tuple[MachineEvent, ...]:
    """One ``StateChangedEvent`` can imply several ``MachineEvent``s: a downtime start/end
    (crossing the production/non-production boundary — reuses
    ``msfc.domain.NON_PRODUCTION_STATES``, not a new list) plus, for the ESTOP/reset cases
    specifically, an ``emergency_stop``/``reset`` marker. Every derived event carries
    ``state=event.to_state`` so :class:`~msfc.analytics.session.ProductionSession` can
    categorize downtime without needing a separate state-tracking channel."""
    events: list[MachineEvent] = []
    from_non_production = event.from_state in NON_PRODUCTION_STATES
    to_non_production = event.to_state in NON_PRODUCTION_STATES

    def _event(event_type: MachineEventType) -> MachineEvent:
        return MachineEvent(event_type, mono_ms, state=event.to_state, detail={"cause": event.cause})

    if event.to_state is MachineState.ESTOP and event.from_state is not MachineState.ESTOP:
        events.append(_event(MachineEventType.EMERGENCY_STOP))
    if event.from_state in (MachineState.ESTOP, MachineState.FAULT, MachineState.SAFE_STOP) and event.to_state not in (
        MachineState.ESTOP, MachineState.FAULT, MachineState.SAFE_STOP,
    ):
        events.append(_event(MachineEventType.RESET))

    if from_non_production and to_non_production and event.from_state is not event.to_state:
        # Crossing between two DIFFERENT non-production states (e.g. ESTOP -> IDLE during
        # recovery) closes the old interval and opens a new one with the new state's own
        # category -- an EMERGENCY_STOP interval and the UNPLANNED interval that follows it
        # are not the same thing for reporting purposes, even though neither is "downtime
        # start" or "downtime end" in the production/non-production sense alone.
        events.append(_event(MachineEventType.DOWNTIME_END))
        events.append(_event(MachineEventType.DOWNTIME_START))
    elif not from_non_production and to_non_production:
        events.append(_event(MachineEventType.DOWNTIME_START))
    elif from_non_production and not to_non_production:
        events.append(_event(MachineEventType.DOWNTIME_END))

    if event.to_state is MachineState.RUNNING and event.from_state is not MachineState.RUNNING:
        events.append(_event(MachineEventType.MACHINE_START))
    if event.from_state is MachineState.RUNNING and event.to_state is not MachineState.RUNNING:
        events.append(_event(MachineEventType.MACHINE_STOP))

    return tuple(events)


def from_product_detected(event: ProductDetectedEvent) -> MachineEvent:
    """A product entering the cell begins one production cycle."""
    return MachineEvent(MachineEventType.CYCLE_START, event.t_detect_mono_ms, product_id=event.product_id)


def from_product_sorted(event: ProductSortedEvent) -> tuple[MachineEvent, ...]:
    """A sorted product completes its cycle and yields exactly one GOOD or DEFECT outcome.

    D-045 (DECISIONS.md): RawVerdict.UNCERTAIN never reaches this function — by the time a
    product is sorted, msfc.decision.DecisionEngine has already resolved any UNCERTAIN
    channel into a final two-valued Verdict (GOOD/DEFECT) per its configured policy
    (FR-DEC-04, default DEFECT). SortAction is likewise only PASSED/REJECTED. A NO_DECISION
    reject (no verdict arrived in time, F033) is fail-closed and counts as a defect here too,
    exactly as it already does in msfc.domain.state.Counters.with_rejected(no_decision=True).
    """
    outcome = (MachineEventType.PRODUCT_GOOD if event.action is SortAction.PASSED
               else MachineEventType.PRODUCT_DEFECT)
    return (
        MachineEvent(MachineEventType.CYCLE_COMPLETE, event.t_s2_mono_ms, product_id=event.product_id,
                     detail={"cycle_time_ms": event.t_s2_mono_ms - event.t_detect_mono_ms}),
        MachineEvent(outcome, event.t_s2_mono_ms, product_id=event.product_id,
                     detail={"reason": event.reason.value}),
    )


def from_fault_report(report: FaultReport, *, mono_ms: int) -> MachineEvent:
    event_type = MachineEventType.FAULT if report.event == "RAISED" else MachineEventType.FAULT_CLEAR
    return MachineEvent(event_type, mono_ms, detail={"fault_code": report.fault.code, "detail": report.detail})
