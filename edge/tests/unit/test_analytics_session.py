"""P4.9 production session/shift + relevant P4.15 edge cases (event ordering, duplicate
events, missing cycle_complete, overlapping downtime, session reset)."""

from __future__ import annotations

import pytest

from msfc.core.errors import OeeError
from msfc.domain import MachineState
from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.models import DowntimeCategory
from msfc.analytics.session import DEFAULT_STATE_CATEGORY, ProductionSession, SessionConfig


def _cycle(product_id: str, start_ms: int, duration_ms: int, good: bool = True) -> list[MachineEvent]:
    end_ms = start_ms + duration_ms
    outcome = MachineEventType.PRODUCT_GOOD if good else MachineEventType.PRODUCT_DEFECT
    return [
        MachineEvent(MachineEventType.CYCLE_START, start_ms, product_id=product_id),
        MachineEvent(MachineEventType.CYCLE_COMPLETE, end_ms, product_id=product_id),
        MachineEvent(outcome, end_ms, product_id=product_id),
    ]


# --------------------------------------------------------------------------- SessionConfig
def test_session_config_rejects_non_positive_planned_time() -> None:
    with pytest.raises(OeeError, match="planned_production_time_ms"):
        SessionConfig(planned_production_time_ms=0, ideal_cycle_time_ms=1_000)


def test_session_config_rejects_non_positive_ideal_cycle_time() -> None:
    with pytest.raises(OeeError, match="ideal_cycle_time_ms"):
        SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=0)


def test_session_config_rejects_slow_cycle_factor_not_above_one() -> None:
    with pytest.raises(OeeError, match="slow_cycle_factor"):
        SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000, slow_cycle_factor=1.0)


def test_session_config_does_not_hard_code_a_real_shift() -> None:
    """P4.9: every boundary is a field, not a constant baked into the class."""
    a = SessionConfig(planned_production_time_ms=8 * 3_600_000, ideal_cycle_time_ms=1_000, name="day-shift")
    b = SessionConfig(planned_production_time_ms=12 * 3_600_000, ideal_cycle_time_ms=1_000, name="night-shift")
    assert a.planned_production_time_ms != b.planned_production_time_ms


# --------------------------------------------------------------------------- basic lifecycle
def test_session_starts_with_zero_counts() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    status = session.status(now_mono_ms=0)
    assert status.cycle_count == 0
    assert status.good_count == 0
    assert status.defect_count == 0


def test_session_accumulates_cycles() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    for e in _cycle("7-1", 0, 1_000, good=True) + _cycle("7-2", 1_000, 1_000, good=False):
        session.record_event(e)
    status = session.status(now_mono_ms=2_000)
    assert status.cycle_count == 2 and status.good_count == 1 and status.defect_count == 1


def test_end_rejects_ended_before_last_event() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 5_000, product_id="7-1"))
    with pytest.raises(OeeError, match="ended_at_mono_ms"):
        session.end(ended_at_mono_ms=1_000)


def test_cannot_record_after_session_ended() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.end(ended_at_mono_ms=1_000)
    with pytest.raises(OeeError, match="ended"):
        session.record_event(MachineEvent(MachineEventType.CYCLE_START, 500, product_id="7-1"))


def test_reset_clears_accumulated_data_and_keeps_config() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    for e in _cycle("7-1", 0, 1_000):
        session.record_event(e)
    assert session.status(now_mono_ms=1_000).cycle_count == 1

    session.reset(now_mono_ms=5_000)
    assert session.status(now_mono_ms=5_000).cycle_count == 0
    assert session.config is config


# --------------------------------------------------------------------------- P4.15: event ordering / duplicates
def test_out_of_order_event_is_rejected() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 5_000, product_id="7-1"))
    with pytest.raises(OeeError, match="out of order"):
        session.record_event(MachineEvent(MachineEventType.CYCLE_START, 4_000, product_id="7-2"))


def test_duplicate_cycle_start_for_the_same_product_is_rejected() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"))
    with pytest.raises(OeeError, match="duplicate cycle_start"):
        session.record_event(MachineEvent(MachineEventType.CYCLE_START, 100, product_id="7-1"))


def test_cycle_complete_without_product_id_is_rejected() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    with pytest.raises(OeeError, match="product_id"):
        session.record_event(MachineEvent(MachineEventType.CYCLE_COMPLETE, 100))


# --------------------------------------------------------------------------- P4.15: missing cycle_complete
def test_cycle_complete_without_matching_cycle_start_is_counted_incomplete_not_crashed() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.CYCLE_COMPLETE, 500, product_id="ghost"))
    stats = session.cycle_statistics()
    assert stats.incomplete_count == 1
    assert stats.count == 0


def test_cycle_start_without_cycle_complete_does_not_count_as_a_finished_cycle() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.CYCLE_START, 0, product_id="7-1"))
    stats = session.cycle_statistics()
    assert stats.count == 0  # still "open" -- not silently treated as complete


# --------------------------------------------------------------------------- downtime intervals
def test_downtime_end_without_open_interval_is_rejected() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    with pytest.raises(OeeError, match="no open downtime"):
        session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 100, state=MachineState.IDLE))


def test_overlapping_downtime_start_is_rejected() -> None:
    """P4.15: overlapping downtime -- a second downtime_start while one is already open must
    not silently open two concurrent intervals (which would double-count downtime)."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 100, state=MachineState.FAULT))
    with pytest.raises(OeeError, match="already open"):
        session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 200, state=MachineState.FAULT))


def test_multiple_sequential_downtime_intervals_all_counted() -> None:
    """P4.14 fixture #15: multiple downtime intervals in one session."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 0, state=MachineState.FAULT))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 1_000, state=MachineState.RUNNING))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 2_000, state=MachineState.IDLE))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 2_500, state=MachineState.RUNNING))
    status = session.status(now_mono_ms=3_000)
    assert status.downtime_ms == 1_500  # 1000 + 500


def test_open_downtime_interval_at_boot_is_categorized_and_measured() -> None:
    """Starting in BOOT (the class default) opens a downtime interval immediately -- proven
    open by measuring it before any downtime_end arrives."""
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0)  # default initial_state=BOOT
    status = session.status(now_mono_ms=500)
    assert status.downtime_ms == 500


def test_planned_downtime_uses_explicit_category_not_state_default() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_START, 0, state=MachineState.IDLE,
                                       category=DowntimeCategory.PLANNED))
    session.record_event(MachineEvent(MachineEventType.DOWNTIME_END, 1_000, state=MachineState.RUNNING))
    # Effective availability math: PLANNED is excluded from the denominator (D-049), so with
    # zero cycles and 1_000ms of PLANNED-only downtime out of 10_000ms planned, the effective
    # window shrinks to 9_000ms and run_time_ms == effective window (no other downtime).
    result = session.calculate_oee(now_mono_ms=1_000)
    assert result.planned_production_time_ms == 9_000
    assert result.downtime_ms == 0


def test_default_state_category_has_no_maintenance_entry() -> None:
    """D-046: MAINTENANCE only ever arrives via an explicit MachineEvent.category override."""
    assert DowntimeCategory.MAINTENANCE not in DEFAULT_STATE_CATEGORY.values()


# --------------------------------------------------------------------------- slow / extreme cycles
def test_extremely_short_cycle_is_recorded_and_flagged_if_below_expectation() -> None:
    config = SessionConfig(planned_production_time_ms=10_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    for e in _cycle("7-1", 0, 1):  # 1 ms cycle
        session.record_event(e)
    stats = session.cycle_statistics()
    assert stats.min_ms == 1
    assert stats.slow_cycle_count == 0


def test_extremely_long_cycle_is_flagged_slow() -> None:
    config = SessionConfig(planned_production_time_ms=100_000, ideal_cycle_time_ms=1_000)
    session = ProductionSession(config, started_at_mono_ms=0, initial_state=MachineState.RUNNING)
    for e in _cycle("7-1", 0, 50_000):
        session.record_event(e)
    stats = session.cycle_statistics()
    assert stats.max_ms == 50_000
    assert stats.slow_cycle_count == 1
