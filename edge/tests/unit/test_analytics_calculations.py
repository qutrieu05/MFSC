"""P4.5 Availability, P4.6 Performance, P4.7 Quality, P4.8 OEE — including P4.15 edge cases
(division by zero, negative duration, zero counts) for this module specifically.
"""

from __future__ import annotations

import pytest

from msfc.core.errors import OeeError
from msfc.analytics.calculations import (
    calculate_availability,
    calculate_oee,
    calculate_performance,
    calculate_quality,
    to_oee_metrics_v1_payload,
)


# --------------------------------------------------------------------------- availability
def test_availability_formula() -> None:
    assert calculate_availability(planned_production_time_ms=10_000, downtime_ms=2_000) == 0.8


def test_availability_zero_downtime_is_full() -> None:
    assert calculate_availability(planned_production_time_ms=10_000, downtime_ms=0) == 1.0


def test_availability_all_downtime_is_zero() -> None:
    assert calculate_availability(planned_production_time_ms=10_000, downtime_ms=10_000) == 0.0


def test_availability_rejects_zero_planned_time() -> None:
    with pytest.raises(OeeError, match="planned_production_time_ms"):
        calculate_availability(planned_production_time_ms=0, downtime_ms=0)


def test_availability_rejects_negative_planned_time() -> None:
    with pytest.raises(OeeError, match="planned_production_time_ms"):
        calculate_availability(planned_production_time_ms=-1, downtime_ms=0)


def test_availability_rejects_negative_downtime() -> None:
    with pytest.raises(OeeError, match="downtime_ms"):
        calculate_availability(planned_production_time_ms=10_000, downtime_ms=-1)


def test_availability_rejects_downtime_exceeding_planned_time() -> None:
    with pytest.raises(OeeError, match="exceeds"):
        calculate_availability(planned_production_time_ms=10_000, downtime_ms=10_001)


# --------------------------------------------------------------------------- performance
def test_performance_formula() -> None:
    assert calculate_performance(ideal_cycle_time_ms=1_000, total_count=8, run_time_ms=10_000) == 0.8


def test_performance_can_exceed_one_and_is_not_clamped() -> None:
    """D-048: a real cycle faster than the configured 'ideal' is not an error."""
    performance = calculate_performance(ideal_cycle_time_ms=1_000, total_count=20, run_time_ms=10_000)
    assert performance == 2.0


def test_performance_zero_count_is_zero() -> None:
    assert calculate_performance(ideal_cycle_time_ms=1_000, total_count=0, run_time_ms=10_000) == 0.0


def test_performance_rejects_zero_run_time() -> None:
    with pytest.raises(OeeError, match="run_time_ms"):
        calculate_performance(ideal_cycle_time_ms=1_000, total_count=5, run_time_ms=0)


def test_performance_rejects_negative_run_time() -> None:
    with pytest.raises(OeeError, match="run_time_ms"):
        calculate_performance(ideal_cycle_time_ms=1_000, total_count=5, run_time_ms=-1)


def test_performance_rejects_zero_ideal_cycle_time() -> None:
    with pytest.raises(OeeError, match="ideal_cycle_time_ms"):
        calculate_performance(ideal_cycle_time_ms=0, total_count=5, run_time_ms=10_000)


def test_performance_rejects_negative_total_count() -> None:
    with pytest.raises(OeeError, match="total_count"):
        calculate_performance(ideal_cycle_time_ms=1_000, total_count=-1, run_time_ms=10_000)


# --------------------------------------------------------------------------- quality
def test_quality_formula() -> None:
    assert calculate_quality(good_count=9, total_count=10) == 0.9


def test_quality_all_good() -> None:
    assert calculate_quality(good_count=10, total_count=10) == 1.0


def test_quality_all_defect() -> None:
    assert calculate_quality(good_count=0, total_count=10) == 0.0


def test_quality_rejects_zero_total_count() -> None:
    with pytest.raises(OeeError, match="total_count"):
        calculate_quality(good_count=0, total_count=0)


def test_quality_rejects_good_count_exceeding_total() -> None:
    with pytest.raises(OeeError, match="good_count"):
        calculate_quality(good_count=11, total_count=10)


def test_quality_rejects_negative_good_count() -> None:
    with pytest.raises(OeeError, match="good_count"):
        calculate_quality(good_count=-1, total_count=10)


# --------------------------------------------------------------------------- oee
def test_oee_multiplies_the_three_factors() -> None:
    result = calculate_oee(
        planned_production_time_ms=10_000, downtime_ms=2_000, ideal_cycle_time_ms=1_000,
        total_count=8, good_count=8,
    )
    assert result.availability == 0.8
    assert result.performance == pytest.approx(1_000 * 8 / 8_000)
    assert result.quality == 1.0
    assert result.oee == pytest.approx(result.availability * result.performance * result.quality)
    assert result.defect_count == 0


def test_oee_zero_total_count_gives_zero_performance_and_quality_not_a_crash() -> None:
    result = calculate_oee(
        planned_production_time_ms=10_000, downtime_ms=0, ideal_cycle_time_ms=1_000,
        total_count=0, good_count=0,
    )
    assert result.performance == 0.0
    assert result.quality == 0.0
    assert result.oee == 0.0


def test_oee_result_carries_the_raw_inputs_for_traceability() -> None:
    result = calculate_oee(
        planned_production_time_ms=10_000, downtime_ms=1_000, ideal_cycle_time_ms=500,
        total_count=15, good_count=12,
    )
    assert result.planned_production_time_ms == 10_000
    assert result.run_time_ms == 9_000
    assert result.downtime_ms == 1_000
    assert result.total_count == 15
    assert result.good_count == 12
    assert result.defect_count == 3


# --------------------------------------------------------------------------- payload clamping (D-048)
def test_payload_clamps_performance_above_one_for_schema_compatibility() -> None:
    result = calculate_oee(
        planned_production_time_ms=10_000, downtime_ms=0, ideal_cycle_time_ms=1_000,
        total_count=20, good_count=20,
    )
    assert result.performance == 2.0  # raw, unclamped
    payload = to_oee_metrics_v1_payload(result)
    assert payload["performance"] == 1.0  # clamped only at the payload boundary
    assert payload["oee"] == 1.0


def test_payload_keys_match_oee_metrics_v1_required_fields() -> None:
    result = calculate_oee(
        planned_production_time_ms=10_000, downtime_ms=0, ideal_cycle_time_ms=1_000,
        total_count=5, good_count=5,
    )
    payload = to_oee_metrics_v1_payload(result)
    assert set(payload) == {"availability", "performance", "quality", "oee"}
    assert all(0.0 <= v <= 1.0 for v in payload.values())
