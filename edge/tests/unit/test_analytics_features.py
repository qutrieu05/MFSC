"""P5.4 feature extraction — including P5.15 edge cases (empty stream, one measurement,
zero variance)."""

from __future__ import annotations

import pytest

from msfc.core.errors import HealthError
from msfc.analytics.features import extract_features
from msfc.analytics.health_models import SensorMeasurement, SensorQuality, SensorType


def _m(value: float, mono_ms: int, quality: SensorQuality = SensorQuality.OK,
       sensor_type: SensorType = SensorType.TEMPERATURE, unit: str = "degC") -> SensorMeasurement:
    return SensorMeasurement(sensor_id="s1", sensor_type=sensor_type, mono_ms=mono_ms, value=value,
                              unit=unit, quality=quality)


def test_extract_features_rejects_inverted_window() -> None:
    with pytest.raises(HealthError, match="window_end_mono_ms"):
        extract_features([], sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                          window_start_mono_ms=1000, window_end_mono_ms=0)


def test_extract_features_rejects_non_positive_moving_average_window() -> None:
    with pytest.raises(HealthError, match="moving_average_window"):
        extract_features([], sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                          window_start_mono_ms=0, window_end_mono_ms=1000, moving_average_window=0)


def test_empty_stream_returns_zero_sample_count_not_a_crash() -> None:
    result = extract_features([], sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=1000)
    assert result.sample_count == 0
    assert result.mean is None
    assert result.minimum is None


def test_non_ok_measurements_are_excluded() -> None:
    measurements = [_m(70, 0), _m(999, 1000, quality=SensorQuality.INVALID), _m(72, 2000)]
    result = extract_features(measurements, sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=2000)
    assert result.sample_count == 2
    assert result.maximum == 72  # the INVALID 999 must not leak into the statistics


def test_one_measurement_has_zero_variance() -> None:
    result = extract_features([_m(70, 0)], sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=0)
    assert result.sample_count == 1
    assert result.mean == 70
    assert result.std_dev == 0.0
    assert result.variance == 0.0
    assert result.rate_of_change is None  # can't compute a rate from a single point


def test_basic_statistics() -> None:
    measurements = [_m(v, i * 1000) for i, v in enumerate([1, 2, 3, 4, 5])]
    result = extract_features(measurements, sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=4000)
    assert result.minimum == 1
    assert result.maximum == 5
    assert result.mean == 3
    assert result.median == 3
    assert result.value_range == 4


def test_rate_of_change_is_first_to_last_over_elapsed_time() -> None:
    measurements = [_m(0, 0), _m(100, 1000)]
    result = extract_features(measurements, sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=1000)
    assert result.rate_of_change == pytest.approx(0.1)  # (100-0)/1000ms


def test_moving_average_uses_the_most_recent_window() -> None:
    measurements = [_m(v, i * 1000) for i, v in enumerate([10, 10, 10, 100, 100])]
    result = extract_features(measurements, sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=4000, moving_average_window=2)
    assert result.moving_average == 100  # average of the last 2: [100, 100]


def test_rms_computed_only_for_vibration() -> None:
    measurements = [_m(3, 0, sensor_type=SensorType.VIBRATION, unit="mm/s"),
                    _m(4, 1000, sensor_type=SensorType.VIBRATION, unit="mm/s")]
    result = extract_features(measurements, sensor_id="vib1", sensor_type=SensorType.VIBRATION,
                               window_start_mono_ms=0, window_end_mono_ms=1000)
    assert result.rms == pytest.approx((3 * 3 + 4 * 4) ** 0.5 / (2 ** 0.5))


def test_rms_is_none_for_non_vibration_sensors() -> None:
    result = extract_features([_m(70, 0)], sensor_id="s1", sensor_type=SensorType.TEMPERATURE,
                               window_start_mono_ms=0, window_end_mono_ms=0)
    assert result.rms is None
