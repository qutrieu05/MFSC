"""P4.1 OEE domain model + P4.4 downtime model + P4.10 cycle statistics."""

from __future__ import annotations

import pytest

from msfc.core.errors import OeeError
from msfc.domain import MachineState
from msfc.analytics.models import CycleStatistics, DowntimeCategory, DowntimeInterval, MachineStatus, OeeResult


def test_downtime_interval_rejects_negative_start() -> None:
    with pytest.raises(OeeError, match="start_mono_ms"):
        DowntimeInterval(category=DowntimeCategory.FAULT, state=MachineState.FAULT, start_mono_ms=-1)


def test_downtime_interval_rejects_end_before_start() -> None:
    with pytest.raises(OeeError, match="end_mono_ms"):
        DowntimeInterval(category=DowntimeCategory.FAULT, state=MachineState.FAULT,
                          start_mono_ms=100, end_mono_ms=50)


def test_downtime_interval_duration_closed() -> None:
    interval = DowntimeInterval(category=DowntimeCategory.FAULT, state=MachineState.FAULT,
                                 start_mono_ms=100, end_mono_ms=300)
    assert interval.duration_ms() == 200


def test_downtime_interval_duration_open_requires_now() -> None:
    interval = DowntimeInterval(category=DowntimeCategory.FAULT, state=MachineState.FAULT, start_mono_ms=100)
    with pytest.raises(OeeError, match="now_mono_ms is required"):
        interval.duration_ms()
    assert interval.duration_ms(now_mono_ms=250) == 150


def test_downtime_interval_open_duration_rejects_now_before_start() -> None:
    interval = DowntimeInterval(category=DowntimeCategory.FAULT, state=MachineState.FAULT, start_mono_ms=100)
    with pytest.raises(OeeError, match="must not be before"):
        interval.duration_ms(now_mono_ms=50)


def test_downtime_category_values() -> None:
    assert {c.value for c in DowntimeCategory} == {
        "PLANNED", "UNPLANNED", "FAULT", "EMERGENCY_STOP", "MAINTENANCE", "IDLE",
    }


def test_cycle_statistics_deviation_from_ideal() -> None:
    stats = CycleStatistics(count=3, ideal_ms=1000, average_ms=1200.0)
    assert stats.deviation_from_ideal_ms == 200.0


def test_cycle_statistics_deviation_none_without_average() -> None:
    stats = CycleStatistics(count=0, ideal_ms=1000)
    assert stats.deviation_from_ideal_ms is None


def test_oee_result_is_a_plain_deterministic_value_object() -> None:
    result = OeeResult(
        availability=0.9, performance=0.8, quality=0.95, oee=0.9 * 0.8 * 0.95,
        planned_production_time_ms=10_000, run_time_ms=9_000, downtime_ms=1_000,
        total_count=10, good_count=9, defect_count=1,
    )
    assert result.oee == pytest.approx(0.684, abs=1e-6)


def test_machine_status_optional_fields_default_to_none() -> None:
    status = MachineStatus(
        state=MachineState.IDLE, session_name=None, cycle_count=0, good_count=0, defect_count=0,
        downtime_ms=0, current_fault=None, last_event_type=None, last_event_mono_ms=None,
    )
    assert status.oee is None
    assert status.cycle_stats is None
