"""P5.5 deterministic machine baseline."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.baseline import HealthBaseline
from msfc.analytics.health_models import SensorType


def test_baseline_rejects_inverted_range() -> None:
    with pytest.raises(HealthError, match="expected_min"):
        HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=100, expected_max=0)


def test_baseline_rejects_negative_reference_std_dev() -> None:
    with pytest.raises(HealthError, match="reference_std_dev"):
        HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=0, expected_max=100,
                        reference_std_dev=-1)


def test_deviation_is_zero_inside_range() -> None:
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)
    assert baseline.deviation(70) == 0.0


def test_deviation_above_range_is_positive() -> None:
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)
    assert baseline.deviation(90) == 10.0


def test_deviation_below_range_is_negative() -> None:
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)
    assert baseline.deviation(50) == -10.0


def test_deviation_at_exact_boundary_is_zero() -> None:
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)
    assert baseline.deviation(60) == 0.0
    assert baseline.deviation(80) == 0.0


def test_z_score_without_reference_stats_is_none() -> None:
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80)
    assert baseline.z_score(70) is None


def test_z_score_with_zero_reference_std_dev_is_none() -> None:
    """A constant reference signal (std_dev=0) would make z-score a division by zero --
    caller should fall back to deviation() instead."""
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80,
                               reference_mean=70, reference_std_dev=0)
    assert baseline.z_score(75) is None


def test_z_score_formula() -> None:
    baseline = HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=60, expected_max=80,
                               reference_mean=70, reference_std_dev=5)
    assert baseline.z_score(80) == pytest.approx(2.0)


def test_baseline_never_hard_codes_a_default_value() -> None:
    """P5.5: no baseline is usable without the caller providing a range -- there is no
    class-level default to accidentally rely on."""
    with pytest.raises(TypeError):
        HealthBaseline(sensor_type=SensorType.TEMPERATURE)  # type: ignore[call-arg]
