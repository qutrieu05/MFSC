"""P5.3 sensor data-quality validation — including several P5.15 edge cases specific to it
(NaN, infinity, impossible value, stale, future timestamp, duplicate, invalid unit)."""

from __future__ import annotations

import math

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.health_models import SensorQuality, SensorType
from msfc.analytics.quality import QualityConfig, assess_quality, build_measurement

CONFIG = QualityConfig(expected_unit="degC", valid_range=(-50.0, 300.0), stale_after_ms=60_000,
                        max_future_skew_ms=1_000)


def test_quality_config_rejects_non_positive_stale_after() -> None:
    with pytest.raises(HealthError, match="stale_after_ms"):
        QualityConfig(expected_unit="degC", stale_after_ms=0)


def test_quality_config_rejects_negative_future_skew() -> None:
    with pytest.raises(HealthError, match="max_future_skew_ms"):
        QualityConfig(expected_unit="degC", max_future_skew_ms=-1)


def test_quality_config_rejects_inverted_valid_range() -> None:
    with pytest.raises(HealthError, match="valid_range"):
        QualityConfig(expected_unit="degC", valid_range=(100.0, 0.0))


def test_missing_value_is_missing() -> None:
    assert assess_quality(value=None, unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG) is SensorQuality.MISSING


def test_wrong_unit_is_invalid_unit() -> None:
    result = assess_quality(value=70.0, unit="degF", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.INVALID_UNIT


def test_nan_is_invalid() -> None:
    result = assess_quality(value=math.nan, unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.INVALID


def test_infinity_is_invalid() -> None:
    result = assess_quality(value=math.inf, unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.INVALID
    result2 = assess_quality(value=-math.inf, unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert result2 is SensorQuality.INVALID


def test_impossible_value_outside_valid_range_is_invalid() -> None:
    result = assess_quality(value=9999.0, unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.INVALID


def test_future_timestamp_is_flagged() -> None:
    result = assess_quality(value=70.0, unit="degC", mono_ms=5_000, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.FUTURE_TIMESTAMP


def test_timestamp_within_future_skew_tolerance_is_ok() -> None:
    result = assess_quality(value=70.0, unit="degC", mono_ms=500, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.OK


def test_duplicate_timestamp_is_flagged() -> None:
    result = assess_quality(value=70.0, unit="degC", mono_ms=1_000, now_mono_ms=1_000, config=CONFIG,
                             last_mono_ms=1_000)
    assert result is SensorQuality.DUPLICATE


def test_stale_reading_is_flagged() -> None:
    result = assess_quality(value=70.0, unit="degC", mono_ms=0, now_mono_ms=120_000, config=CONFIG)
    assert result is SensorQuality.STALE


def test_fresh_reading_is_ok() -> None:
    result = assess_quality(value=70.0, unit="degC", mono_ms=59_000, now_mono_ms=60_000, config=CONFIG)
    assert result is SensorQuality.OK


def test_build_measurement_preserves_a_safe_zero_for_invalid_value() -> None:
    measurement = build_measurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, value=math.nan,
                                     unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert measurement.quality is SensorQuality.INVALID
    assert measurement.value == 0.0  # never a NaN leaking downstream


def test_build_measurement_preserves_a_real_value_when_ok() -> None:
    measurement = build_measurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, value=72.5,
                                     unit="degC", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert measurement.quality is SensorQuality.OK
    assert measurement.value == 72.5


def test_priority_order_missing_before_invalid_unit() -> None:
    """A None value is MISSING regardless of what the unit says."""
    result = assess_quality(value=None, unit="wrong-unit", mono_ms=0, now_mono_ms=0, config=CONFIG)
    assert result is SensorQuality.MISSING
