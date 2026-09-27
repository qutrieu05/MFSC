"""Deterministic OEE simulation (P4.13) — no real hardware required.

Builder functions produce plain tuples of :class:`~msfc.analytics.events.MachineEvent`; the
named scenario functions below compose them into the 10 situations the PO named. Every
timestamp is an explicit integer argument or a fixed local constant — nothing here reads the
host clock, so re-running any scenario produces byte-identical events every time (P4.13/P4.14).

Every scenario's ``SessionConfig.planned_production_time_ms`` is sized to that scenario's own
event span (not one shared arbitrary constant) so the resulting OEE numbers are directly
interpretable (e.g. "normal production" reads close to 1.0, not diluted by an unrelated
idle tail) — see each function's docstring for the hand-checkable expected shape.
"""

from __future__ import annotations

from msfc.domain import MachineState
from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.models import DowntimeCategory
from msfc.analytics.session import SessionConfig

GOOD = "GOOD"
DEFECT = "DEFECT"


def make_cycle_events(product_id: str, *, start_mono_ms: int, duration_ms: int, verdict: str) -> tuple[MachineEvent, ...]:
    end_mono_ms = start_mono_ms + duration_ms
    outcome = MachineEventType.PRODUCT_GOOD if verdict == GOOD else MachineEventType.PRODUCT_DEFECT
    return (
        MachineEvent(MachineEventType.CYCLE_START, start_mono_ms, product_id=product_id),
        MachineEvent(MachineEventType.CYCLE_COMPLETE, end_mono_ms, product_id=product_id,
                     detail={"cycle_time_ms": duration_ms}),
        MachineEvent(outcome, end_mono_ms, product_id=product_id, detail={"reason": f"VERDICT_{verdict}"}),
    )


def make_downtime_events(*, start_mono_ms: int, end_mono_ms: int, state: MachineState,
                          resumes_to: MachineState = MachineState.RUNNING,
                          category: DowntimeCategory | None = None) -> tuple[MachineEvent, ...]:
    return (
        MachineEvent(MachineEventType.DOWNTIME_START, start_mono_ms, state=state, category=category),
        MachineEvent(MachineEventType.DOWNTIME_END, end_mono_ms, state=resumes_to),
    )


def make_fault_events(*, raised_mono_ms: int, cleared_mono_ms: int, fault_code: str) -> tuple[MachineEvent, ...]:
    return (
        MachineEvent(MachineEventType.FAULT, raised_mono_ms, detail={"fault_code": fault_code}),
        MachineEvent(MachineEventType.FAULT_CLEAR, cleared_mono_ms, detail={"fault_code": fault_code}),
    )


def scenario_normal_production() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """10 back-to-back GOOD cycles at exactly the ideal cycle time, span = 10_000 ms,
    planned_production_time_ms = 10_000 -> availability=performance=quality=oee=1.0."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000, name="normal_production")
    events: list[MachineEvent] = []
    for i in range(10):
        events.extend(make_cycle_events(f"7-{i}", start_mono_ms=i * 1_000, duration_ms=1_000, verdict=GOOD))
    return config, tuple(events)


def scenario_normal_cycles() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """Same shape as normal_production but with natural cycle-to-cycle variance (avg ~= ideal)."""
    durations = (950, 1_000, 1_050, 980, 1_020)  # sums to 5_000
    config = SessionConfig(planned_production_time_ms=sum(durations), ideal_cycle_time_ms=1_000, name="normal_cycles")
    events: list[MachineEvent] = []
    t = 0
    for i, duration in enumerate(durations):
        events.extend(make_cycle_events(f"7-{i}", start_mono_ms=t, duration_ms=duration, verdict=GOOD))
        t += duration
    return config, tuple(events)


def scenario_planned_downtime() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """2 cycles, a 10_000 ms PLANNED break (explicit category — no MachineState maps to
    PLANNED by itself, D-046), then 2 more cycles. Classical OEE excludes PLANNED downtime
    from Planned Production Time itself (D-049): effective window = 14_000 - 10_000 = 4_000 ms
    exactly matches the 4 cycles' span -> availability=performance=quality=oee=1.0, proving
    the planned break did NOT penalize availability (contrast with unplanned_downtime below)."""
    config = SessionConfig(planned_production_time_ms=14_000, ideal_cycle_time_ms=1_000, name="planned_downtime")
    events: list[MachineEvent] = []
    events.extend(make_cycle_events("7-1", start_mono_ms=0, duration_ms=1_000, verdict=GOOD))
    events.extend(make_cycle_events("7-2", start_mono_ms=1_000, duration_ms=1_000, verdict=GOOD))
    events.extend(make_downtime_events(start_mono_ms=2_000, end_mono_ms=12_000, state=MachineState.IDLE,
                                        category=DowntimeCategory.PLANNED))
    events.extend(make_cycle_events("7-3", start_mono_ms=12_000, duration_ms=1_000, verdict=GOOD))
    events.extend(make_cycle_events("7-4", start_mono_ms=13_000, duration_ms=1_000, verdict=GOOD))
    return config, tuple(events)


def scenario_unplanned_downtime() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """Same shape as planned_downtime (2 cycles, a 10_000 ms gap, 2 more cycles) but the gap
    is UNPLANNED (derived from FAULT state, not an explicit category) -- unlike PLANNED,
    this DOES count against availability: effective window stays the full 14_000 ms, run
    time = 14_000 - 10_000 = 4_000 -> availability = 4_000/14_000 ~= 0.286, while
    performance/quality stay 1.0 (the production that did happen was perfect)."""
    config = SessionConfig(planned_production_time_ms=14_000, ideal_cycle_time_ms=1_000, name="unplanned_downtime")
    events: list[MachineEvent] = []
    events.extend(make_cycle_events("7-1", start_mono_ms=0, duration_ms=1_000, verdict=GOOD))
    events.extend(make_cycle_events("7-2", start_mono_ms=1_000, duration_ms=1_000, verdict=GOOD))
    events.extend(make_downtime_events(start_mono_ms=2_000, end_mono_ms=12_000, state=MachineState.FAULT))
    events.extend(make_cycle_events("7-3", start_mono_ms=12_000, duration_ms=1_000, verdict=GOOD))
    events.extend(make_cycle_events("7-4", start_mono_ms=13_000, duration_ms=1_000, verdict=GOOD))
    return config, tuple(events)


def scenario_machine_fault() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """A fault raised/cleared alongside the matching downtime interval -- pure downtime, no
    cycles (total_count=0 is a valid, deterministic result: performance=quality=0, not a
    crash — see calculate_oee's zero-count branch)."""
    config = SessionConfig(planned_production_time_ms=3_000, ideal_cycle_time_ms=1_000, name="machine_fault")
    events = list(make_fault_events(raised_mono_ms=1_000, cleared_mono_ms=3_000, fault_code="F010"))
    events.extend(make_downtime_events(start_mono_ms=1_000, end_mono_ms=3_000, state=MachineState.FAULT))
    events.sort(key=lambda e: e.mono_ms)
    return config, tuple(events)


def scenario_emergency_stop() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """ESTOP engaged then reset -- pure downtime, no cycles (an E-STOP inherently means
    nothing was produced during it)."""
    config = SessionConfig(planned_production_time_ms=4_000, ideal_cycle_time_ms=1_000, name="emergency_stop")
    events = (
        MachineEvent(MachineEventType.EMERGENCY_STOP, 0, state=MachineState.ESTOP),
        MachineEvent(MachineEventType.DOWNTIME_START, 0, state=MachineState.ESTOP),
        MachineEvent(MachineEventType.RESET, 4_000, state=MachineState.IDLE),
        MachineEvent(MachineEventType.DOWNTIME_END, 4_000, state=MachineState.IDLE),
    )
    return config, events


def scenario_defect_production() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """5 DEFECT cycles at the ideal cycle time -- availability=performance=1.0, quality=0.0
    -> OEE=0.0, isolating the quality factor from the other two."""
    config = SessionConfig(planned_production_time_ms=5_000, ideal_cycle_time_ms=1_000, name="defect_production")
    events: list[MachineEvent] = []
    for i in range(5):
        events.extend(make_cycle_events(f"7-{i}", start_mono_ms=i * 1_000, duration_ms=1_000, verdict=DEFECT))
    return config, tuple(events)


def scenario_mixed_good_defect_production() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """8 cycles, 5 GOOD + 3 DEFECT -> quality = 5/8 = 0.625, availability=performance=1.0."""
    verdicts = (GOOD, GOOD, DEFECT, GOOD, DEFECT, GOOD, GOOD, DEFECT)
    config = SessionConfig(planned_production_time_ms=len(verdicts) * 1_000, ideal_cycle_time_ms=1_000,
                            name="mixed_good_defect")
    events: list[MachineEvent] = []
    for i, verdict in enumerate(verdicts):
        events.extend(make_cycle_events(f"7-{i}", start_mono_ms=i * 1_000, duration_ms=1_000, verdict=verdict))
    return config, tuple(events)


def scenario_slow_cycles() -> tuple[SessionConfig, tuple[MachineEvent, ...]]:
    """4 GOOD cycles at 2x the ideal cycle time -- all flagged slow (default slow_cycle_factor
    1.5), performance = (1000*4)/8000 = 0.5, availability=quality=1.0 -> OEE=0.5."""
    config = SessionConfig(planned_production_time_ms=8_000, ideal_cycle_time_ms=1_000, name="slow_cycles")
    events: list[MachineEvent] = []
    t = 0
    for i in range(4):
        events.extend(make_cycle_events(f"7-{i}", start_mono_ms=t, duration_ms=2_000, verdict=GOOD))
        t += 2_000
    return config, tuple(events)


def scenario_multiple_production_sessions() -> tuple[tuple[SessionConfig, tuple[MachineEvent, ...]], ...]:
    """Two independent sessions -- P4.9: "the system must correctly handle multiple
    production sessions." Each session's own event stream starts its own mono_ms range,
    matching how a real reset (or a new shift with its own reference clock) would look."""
    session_a_config = SessionConfig(planned_production_time_ms=1_000, ideal_cycle_time_ms=1_000, name="shift-a")
    session_a_events = make_cycle_events("7-1", start_mono_ms=0, duration_ms=1_000, verdict=GOOD)

    session_b_config = SessionConfig(planned_production_time_ms=1_000, ideal_cycle_time_ms=1_000, name="shift-b")
    session_b_events = make_cycle_events("8-1", start_mono_ms=0, duration_ms=1_000, verdict=DEFECT)

    return (session_a_config, session_a_events), (session_b_config, session_b_events)
