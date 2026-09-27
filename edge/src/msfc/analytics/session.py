"""Production session / shift (P4.9) — accumulates a MachineEvent stream deterministically.

Reuses ``msfc.domain.state.Counters`` (detected/passed/rejected/no_decision) directly rather
than inventing a parallel counting type (P4.16) — ``total_count``/``good_count``/
``defect_count`` (the PO's OEE vocabulary) are derived from it, documented once here:
total=detected, good=passed, defect=rejected (rejected already includes NO_DECISION rejects,
consistent with the fail-closed policy already established in msfc.decision/msfc.sim).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from msfc.core.errors import OeeError
from msfc.domain import Counters, MachineState
from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.models import CycleStatistics, DowntimeCategory, DowntimeInterval, MachineStatus, OeeResult
from msfc.analytics.calculations import calculate_oee

#: State -> downtime category, or None if that state counts as run time (P4.4/P4.16: reuses
#: MachineState, not a new enum). Deliberately a plain dict, not hard-coded logic, so a caller
#: can override the interpretation for one session (P4.4: "do not invent industrial
#: assumptions silently" -- this IS the assumption, made explicit and overridable). BOOT/
#: SELF_TEST/IDLE default to UNPLANNED (nothing marks them PLANNED unless the caller
#: reclassifies a specific interval after the fact -- see ProductionSession.reclassify_downtime).
#: STARTING/STOPPING count as run time: the machine is actively transitioning under its own
#: motion, not idle (documented assumption, D-047).
DEFAULT_STATE_CATEGORY: Mapping[MachineState, DowntimeCategory | None] = {
    MachineState.BOOT: DowntimeCategory.UNPLANNED,
    MachineState.SELF_TEST: DowntimeCategory.UNPLANNED,
    MachineState.IDLE: DowntimeCategory.UNPLANNED,
    MachineState.STARTING: None,
    MachineState.RUNNING: None,
    MachineState.STOPPING: None,
    MachineState.SAFE_STOP: DowntimeCategory.FAULT,
    MachineState.FAULT: DowntimeCategory.FAULT,
    MachineState.ESTOP: DowntimeCategory.EMERGENCY_STOP,
}


@dataclass(frozen=True, slots=True)
class SessionConfig:
    """Never a hard-coded real-world shift (P4.9) — every boundary/parameter is a field."""

    planned_production_time_ms: int
    ideal_cycle_time_ms: int
    name: str = "default"
    slow_cycle_factor: float = 1.5  # a cycle > ideal * this factor is flagged "slow" (P4.10)

    def __post_init__(self) -> None:
        if self.planned_production_time_ms <= 0:
            raise OeeError(f"planned_production_time_ms must be > 0, got {self.planned_production_time_ms!r}")
        if self.ideal_cycle_time_ms <= 0:
            raise OeeError(f"ideal_cycle_time_ms must be > 0, got {self.ideal_cycle_time_ms!r}")
        if self.slow_cycle_factor <= 1.0:
            raise OeeError(f"slow_cycle_factor must be > 1.0, got {self.slow_cycle_factor!r}")


class ProductionSession:
    """Mutable accumulator (P4.9) — the only stateful object in msfc.analytics. Processes a
    MachineEvent stream one event at a time; every method is deterministic given the same
    event sequence (P4.13/P4.14's simulations depend on this)."""

    def __init__(
        self,
        config: SessionConfig,
        *,
        started_at_mono_ms: int,
        initial_state: MachineState = MachineState.BOOT,
        state_category: Mapping[MachineState, DowntimeCategory | None] | None = None,
    ) -> None:
        self.config = config
        self._state_category = dict(state_category) if state_category is not None else dict(DEFAULT_STATE_CATEGORY)
        self._started_at_mono_ms = started_at_mono_ms
        self._ended_at_mono_ms: int | None = None
        self._last_mono_ms = started_at_mono_ms
        self._state = initial_state
        self._counters = Counters()
        self._closed_downtime: list[DowntimeInterval] = []
        self._open_downtime: DowntimeInterval | None = None
        self._open_cycles: dict[str, int] = {}
        self._cycle_durations_ms: list[int] = []
        self._incomplete_cycle_count = 0
        self._slow_cycle_count = 0
        self._current_fault: str | None = None
        self._last_event: MachineEvent | None = None

        category = self._state_category.get(initial_state)
        if category is not None:
            self._open_downtime = DowntimeInterval(category=category, state=initial_state,
                                                     start_mono_ms=started_at_mono_ms)

    # ------------------------------------------------------------------------- event intake
    def record_event(self, event: MachineEvent) -> None:
        if self._ended_at_mono_ms is not None:
            raise OeeError("cannot record an event after the session has ended")
        if event.mono_ms < self._last_mono_ms:
            raise OeeError(
                f"event out of order: mono_ms {event.mono_ms} is before last recorded {self._last_mono_ms}"
            )
        self._last_mono_ms = event.mono_ms
        self._last_event = event
        if event.state is not None:
            self._state = event.state

        handler = self._HANDLERS.get(event.type)
        if handler is not None:
            handler(self, event)

    def _on_cycle_start(self, event: MachineEvent) -> None:
        if event.product_id is None:
            raise OeeError("cycle_start event requires product_id")
        if event.product_id in self._open_cycles:
            raise OeeError(f"duplicate cycle_start for product_id {event.product_id!r} (P4.15: duplicate events)")
        self._open_cycles[event.product_id] = event.mono_ms
        self._counters = self._counters.with_detected()

    def _on_cycle_complete(self, event: MachineEvent) -> None:
        if event.product_id is None:
            raise OeeError("cycle_complete event requires product_id")
        start = self._open_cycles.pop(event.product_id, None)
        if start is None:
            # P4.15: cycle_complete with no matching cycle_start -- recorded as incomplete/
            # anomalous rather than silently timed as a (meaningless) zero/negative duration.
            self._incomplete_cycle_count += 1
            return
        duration_ms = event.mono_ms - start
        self._cycle_durations_ms.append(duration_ms)
        if duration_ms > self.config.ideal_cycle_time_ms * self.config.slow_cycle_factor:
            self._slow_cycle_count += 1

    def _on_product_good(self, event: MachineEvent) -> None:
        self._counters = self._counters.with_passed()

    def _on_product_defect(self, event: MachineEvent) -> None:
        no_decision = event.detail.get("reason") == "NO_DECISION"
        self._counters = self._counters.with_rejected(no_decision=no_decision)

    def _on_downtime_start(self, event: MachineEvent) -> None:
        if self._open_downtime is not None:
            raise OeeError("downtime_start received while a downtime interval is already open")
        state = event.state if event.state is not None else self._state
        if event.category is not None:
            category = event.category  # explicit override -- e.g. PLANNED/MAINTENANCE
        else:
            category = self._state_category.get(state, DowntimeCategory.UNPLANNED) or DowntimeCategory.UNPLANNED
        self._open_downtime = DowntimeInterval(category=category, state=state, start_mono_ms=event.mono_ms)

    def _on_downtime_end(self, event: MachineEvent) -> None:
        if self._open_downtime is None:
            raise OeeError("downtime_end received with no open downtime interval")
        self._closed_downtime.append(replace(self._open_downtime, end_mono_ms=event.mono_ms))
        self._open_downtime = None

    def _on_fault(self, event: MachineEvent) -> None:
        self._current_fault = str(event.detail.get("fault_code", "UNKNOWN"))

    def _on_fault_clear(self, event: MachineEvent) -> None:
        self._current_fault = None

    _HANDLERS = {
        MachineEventType.CYCLE_START: _on_cycle_start,
        MachineEventType.CYCLE_COMPLETE: _on_cycle_complete,
        MachineEventType.PRODUCT_GOOD: _on_product_good,
        MachineEventType.PRODUCT_DEFECT: _on_product_defect,
        MachineEventType.DOWNTIME_START: _on_downtime_start,
        MachineEventType.DOWNTIME_END: _on_downtime_end,
        MachineEventType.FAULT: _on_fault,
        MachineEventType.FAULT_CLEAR: _on_fault_clear,
    }

    # ------------------------------------------------------------------------- lifecycle
    def end(self, *, ended_at_mono_ms: int) -> None:
        if ended_at_mono_ms < self._last_mono_ms:
            raise OeeError("ended_at_mono_ms must not be before the last recorded event")
        self._ended_at_mono_ms = ended_at_mono_ms

    def reset(self, *, now_mono_ms: int) -> None:
        """Discard all accumulated production data and start a fresh session at
        ``now_mono_ms``, keeping the same config (P4.9: sessions must be resettable)."""
        self.__init__(self.config, started_at_mono_ms=now_mono_ms, initial_state=self._state,  # type: ignore[misc]
                      state_category=self._state_category)

    # ------------------------------------------------------------------------- read models
    @property
    def state(self) -> MachineState:
        return self._state

    #: Categories excluded from the availability *denominator* itself, matching classical
    #: Nakajima OEE's definition of "Planned Production Time" (it already excludes scheduled
    #: non-production time such as breaks/scheduled maintenance) -- NOT the same as being
    #: subtracted from Run Time. See D-049 (DECISIONS.md) for why this split exists
    #: rather than treating every downtime category identically.
    _EXCLUDED_FROM_PLANNED_TIME = frozenset({DowntimeCategory.PLANNED, DowntimeCategory.MAINTENANCE})

    def _downtime_ms(self, *, now_mono_ms: int) -> tuple[int, int]:
        """Returns (excluded_ms, counted_ms): excluded_ms shrinks the availability
        denominator (planned production time); counted_ms is subtracted from it to get run
        time -- see calculate_oee() below."""
        intervals = list(self._closed_downtime)
        if self._open_downtime is not None:
            intervals.append(replace(self._open_downtime, end_mono_ms=now_mono_ms))
        excluded_ms = sum(i.duration_ms() for i in intervals if i.category in self._EXCLUDED_FROM_PLANNED_TIME)
        counted_ms = sum(i.duration_ms() for i in intervals if i.category not in self._EXCLUDED_FROM_PLANNED_TIME)
        return excluded_ms, counted_ms

    def cycle_statistics(self) -> CycleStatistics:
        durations = self._cycle_durations_ms
        return CycleStatistics(
            count=len(durations),
            ideal_ms=self.config.ideal_cycle_time_ms,
            min_ms=min(durations) if durations else None,
            max_ms=max(durations) if durations else None,
            average_ms=(sum(durations) / len(durations)) if durations else None,
            slow_cycle_count=self._slow_cycle_count,
            incomplete_count=self._incomplete_cycle_count,
        )

    def calculate_oee(self, *, now_mono_ms: int) -> OeeResult:
        excluded_ms, counted_ms = self._downtime_ms(now_mono_ms=now_mono_ms)
        effective_planned_ms = self.config.planned_production_time_ms - excluded_ms
        if effective_planned_ms <= 0:
            raise OeeError(
                f"PLANNED/MAINTENANCE downtime ({excluded_ms} ms) consumed the entire "
                f"planned_production_time_ms ({self.config.planned_production_time_ms})"
            )
        return calculate_oee(
            planned_production_time_ms=effective_planned_ms,
            downtime_ms=counted_ms,
            ideal_cycle_time_ms=self.config.ideal_cycle_time_ms,
            total_count=self._counters.detected,
            good_count=self._counters.passed,
        )

    def status(self, *, now_mono_ms: int) -> MachineStatus:
        _excluded_ms, counted_ms = self._downtime_ms(now_mono_ms=now_mono_ms)
        return MachineStatus(
            state=self._state,
            session_name=self.config.name,
            cycle_count=self._counters.detected,
            good_count=self._counters.passed,
            defect_count=self._counters.rejected,
            downtime_ms=counted_ms,
            current_fault=self._current_fault,
            last_event_type=self._last_event.type.value if self._last_event else None,
            last_event_mono_ms=self._last_event.mono_ms if self._last_event else None,
            oee=self.calculate_oee(now_mono_ms=now_mono_ms),
            cycle_stats=self.cycle_statistics(),
        )
