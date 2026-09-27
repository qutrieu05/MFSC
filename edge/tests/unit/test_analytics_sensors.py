"""P5.2 sensor abstraction."""

from __future__ import annotations

from msfc.analytics.health_models import SensorMeasurement, SensorQuality, SensorType
from msfc.analytics.sensors import FixedSequenceSensorSource


def test_fixed_sequence_source_replays_in_order() -> None:
    measurements = [
        SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=70.0, unit="degC"),
        SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=1000, value=71.0, unit="degC"),
    ]
    source = FixedSequenceSensorSource("s1", SensorType.TEMPERATURE, measurements)
    assert source.read(mono_ms=0).value == 70.0
    assert source.read(mono_ms=1000).value == 71.0


def test_fixed_sequence_source_reports_remaining() -> None:
    measurements = [
        SensorMeasurement(sensor_id="s1", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=70.0, unit="degC"),
    ]
    source = FixedSequenceSensorSource("s1", SensorType.TEMPERATURE, measurements)
    assert source.remaining() == 1
    source.read(mono_ms=0)
    assert source.remaining() == 0


def test_fixed_sequence_source_returns_unavailable_after_exhausted() -> None:
    source = FixedSequenceSensorSource("s1", SensorType.TEMPERATURE, [])
    result = source.read(mono_ms=500)
    assert result.quality is SensorQuality.UNAVAILABLE
    assert result.mono_ms == 500


def test_sensor_source_exposes_id_and_type() -> None:
    source = FixedSequenceSensorSource("temp01", SensorType.TEMPERATURE, [])
    assert source.sensor_id == "temp01"
    assert source.sensor_type is SensorType.TEMPERATURE
