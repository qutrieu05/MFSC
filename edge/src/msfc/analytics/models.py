"""OEE / machine-monitoring domain model (P4.1, P4.4, P4.10, P4.11).

Units, documented once here rather than repeated on every field: every duration is
milliseconds on the Cell Controller's own monotonic clock (ARCHITECTURE.md section 5.1, the
same convention every other msfc.domain timestamp already uses) — never wall-clock/host time.
Every ratio (availability/performance/quality) is a plain float, 0.0 = 0%, 1.0 = 100%
(matching contracts/schemas/oee_metrics.v1.json's existing draft field shapes) — except
``performance``/``oee`` which this implementation does NOT clamp to 1.0 (see D-048,
DECISIONS.md: a real cycle faster than the configured "ideal" is possible and is not an
error; clamping only happens at the optional wire-payload boundary,
:func:`msfc.analytics.calculations.to_oee_metrics_v1_payload`).

Reuses ``msfc.domain`` wherever a compatible concept already exists (P4.16): machine state is
``msfc.domain.enums.MachineState`` (not a new enum), and production counts are
``msfc.domain.state.Counters`` (detected/passed/rejected/no_decision) — see
:mod:`msfc.analytics.session` for how those map to OEE's total/good/defect count vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from msfc.core.errors import OeeError
from msfc.domain import MachineState


class DowntimeCategory(str, Enum):
    """How one interval of non-production time counts toward OEE (P4.4).

    Not a replacement for ``MachineState`` — a *classification* of an interval, independent
    of exactly which non-production state the machine was in during it (see
    :data:`msfc.analytics.session.DEFAULT_STATE_CATEGORY` for the state -> category mapping,
    and D-046 for why MAINTENANCE is a downtime tag rather than a new MachineState value).
    """

    PLANNED = "PLANNED"
    UNPLANNED = "UNPLANNED"
    FAULT = "FAULT"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    MAINTENANCE = "MAINTENANCE"
    IDLE = "IDLE"


@dataclass(frozen=True, slots=True)
class DowntimeInterval:
    """One contiguous span of non-production time. ``end_mono_ms is None`` means the
    interval is still open (the machine hasn't left that state yet)."""

    category: DowntimeCategory
    state: MachineState
    start_mono_ms: int
    end_mono_ms: int | None = None
    cause: str = ""

    def __post_init__(self) -> None:
        if self.start_mono_ms < 0:
            raise OeeError(f"start_mono_ms must be >= 0, got {self.start_mono_ms!r}")
        if self.end_mono_ms is not None and self.end_mono_ms < self.start_mono_ms:
            raise OeeError("end_mono_ms must not be before start_mono_ms")

    def duration_ms(self, *, now_mono_ms: int | None = None) -> int:
        """Duration so far. For an open interval, pass ``now_mono_ms`` (required) to get its
        duration up to now; a closed interval ignores ``now_mono_ms``."""
        if self.end_mono_ms is not None:
            return self.end_mono_ms - self.start_mono_ms
        if now_mono_ms is None:
            raise OeeError("now_mono_ms is required to measure an open (still-ongoing) interval")
        if now_mono_ms < self.start_mono_ms:
            raise OeeError("now_mono_ms must not be before the interval's start_mono_ms")
        return now_mono_ms - self.start_mono_ms


@dataclass(frozen=True, slots=True)
class CycleStatistics:
    """Cycle-time monitoring (P4.10) — NOT predictive maintenance (Phase 5's job)."""

    count: int
    ideal_ms: int
    min_ms: int | None = None
    max_ms: int | None = None
    average_ms: float | None = None
    slow_cycle_count: int = 0  # cycles exceeding slow_cycle_threshold_ms (see session.py)
    incomplete_count: int = 0  # cycle_start with no matching cycle_complete

    @property
    def deviation_from_ideal_ms(self) -> float | None:
        if self.average_ms is None:
            return None
        return self.average_ms - self.ideal_ms


@dataclass(frozen=True, slots=True)
class OeeResult:
    """P4.8's deterministic OEE result object. Field names match the PO's explicit list;
    ``availability``/``performance``/``quality``/``oee`` match
    contracts/schemas/oee_metrics.v1.json's already-drafted field names exactly."""

    availability: float
    performance: float
    quality: float
    oee: float
    planned_production_time_ms: int
    run_time_ms: int
    downtime_ms: int
    total_count: int
    good_count: int
    defect_count: int


@dataclass(frozen=True, slots=True)
class MachineStatus:
    """P4.11's monitoring snapshot — current state, independent of physical hardware (built
    from whatever fed msfc.analytics its event stream: a simulator today, real firmware
    later, same interface either way)."""

    state: MachineState
    session_name: str | None
    cycle_count: int
    good_count: int
    defect_count: int
    downtime_ms: int
    current_fault: str | None
    last_event_type: str | None
    last_event_mono_ms: int | None
    oee: OeeResult | None = None
    cycle_stats: CycleStatistics | None = None
