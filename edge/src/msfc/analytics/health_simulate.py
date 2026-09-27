"""Deterministic machine-health simulation (P5.13) — no randomness anywhere, so every
scenario is byte-identical on every run (P5.13: "if random generation is used, fix the seed
and document it" -- this implementation simply doesn't use randomness at all, the simplest way
to guarantee that).
"""

from __future__ import annotations

from typing import Sequence

from msfc.analytics.health_models import SensorMeasurement, SensorQuality, SensorType


def _series(sensor_id: str, sensor_type: SensorType, unit: str, values: Sequence[float], *,
            start_mono_ms: int = 0, step_ms: int = 1_000,
            quality: SensorQuality = SensorQuality.OK) -> tuple[SensorMeasurement, ...]:
    return tuple(
        SensorMeasurement(sensor_id=sensor_id, sensor_type=sensor_type, mono_ms=start_mono_ms + i * step_ms,
                           value=v, unit=unit, quality=quality)
        for i, v in enumerate(values)
    )


# --------------------------------------------------------------------------- 1-3: temperature
def scenario_normal_temperature() -> tuple[SensorMeasurement, ...]:
    return _series("temp01", SensorType.TEMPERATURE, "degC", [70, 71, 70, 69, 70, 71, 70])


def scenario_rising_temperature() -> tuple[SensorMeasurement, ...]:
    return _series("temp01", SensorType.TEMPERATURE, "degC", [70, 75, 80, 85, 90, 95, 100])


def scenario_temperature_spike() -> tuple[SensorMeasurement, ...]:
    return _series("temp01", SensorType.TEMPERATURE, "degC", [70, 70, 70, 150, 70, 70, 70])


# --------------------------------------------------------------------------- 4-6: motor current
def scenario_normal_motor_current() -> tuple[SensorMeasurement, ...]:
    return _series("current01", SensorType.CURRENT, "A", [2.0, 2.1, 2.0, 1.9, 2.0, 2.1, 2.0])


def scenario_increasing_motor_current() -> tuple[SensorMeasurement, ...]:
    return _series("current01", SensorType.CURRENT, "A", [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0])


def scenario_current_spike() -> tuple[SensorMeasurement, ...]:
    return _series("current01", SensorType.CURRENT, "A", [2.0, 2.0, 2.0, 12.0, 2.0, 2.0, 2.0])


# --------------------------------------------------------------------------- 7-9: vibration
def scenario_normal_vibration() -> tuple[SensorMeasurement, ...]:
    return _series("vib01", SensorType.VIBRATION, "mm/s", [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0])


def scenario_increasing_vibration() -> tuple[SensorMeasurement, ...]:
    return _series("vib01", SensorType.VIBRATION, "mm/s", [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0])


def scenario_vibration_spike() -> tuple[SensorMeasurement, ...]:
    return _series("vib01", SensorType.VIBRATION, "mm/s", [1.0, 1.0, 1.0, 9.0, 1.0, 1.0, 1.0])


# --------------------------------------------------------------------------- 10-12: sensor problems
def scenario_sensor_failure() -> tuple[SensorMeasurement, ...]:
    return _series("temp01", SensorType.TEMPERATURE, "degC", [0.0] * 5, quality=SensorQuality.UNAVAILABLE)


def scenario_missing_sensor_data() -> tuple[SensorMeasurement, ...]:
    return _series("temp01", SensorType.TEMPERATURE, "degC", [0.0] * 5, quality=SensorQuality.MISSING)


def scenario_stale_sensor_data() -> tuple[SensorMeasurement, ...]:
    """Readings whose own mono_ms is far in the past relative to whenever a caller evaluates
    them "now" -- msfc.analytics.quality.assess_quality is what actually classifies staleness
    from a (value, mono_ms, now_mono_ms) triple; this fixture pre-tags STALE directly so
    downstream (feature extraction / anomaly detection) tests don't need to also re-derive it."""
    return _series("temp01", SensorType.TEMPERATURE, "degC", [70, 70, 70], start_mono_ms=0, step_ms=1_000,
                    quality=SensorQuality.STALE)


# --------------------------------------------------------------------------- 13: multiple simultaneous anomalies
def scenario_multiple_simultaneous_anomalies() -> dict[str, tuple[SensorMeasurement, ...]]:
    return {
        "temp01": _series("temp01", SensorType.TEMPERATURE, "degC", [70, 70, 70, 150]),
        "current01": _series("current01", SensorType.CURRENT, "A", [2.0, 2.0, 2.0, 12.0]),
        "vib01": _series("vib01", SensorType.VIBRATION, "mm/s", [1.0, 1.0, 1.0, 9.0]),
    }


# --------------------------------------------------------------------------- 14: recovery after anomaly
def scenario_recovery_after_anomaly() -> tuple[SensorMeasurement, ...]:
    return _series("temp01", SensorType.TEMPERATURE, "degC", [70, 70, 150, 150, 70, 70, 70])


# --------------------------------------------------------------------------- 15: critical machine condition
def scenario_critical_machine_condition() -> dict[str, tuple[SensorMeasurement, ...]]:
    return {
        "temp01": _series("temp01", SensorType.TEMPERATURE, "degC", [70, 90, 130, 180]),
        "current01": _series("current01", SensorType.CURRENT, "A", [2.0, 5.0, 10.0, 18.0]),
        "vib01": _series("vib01", SensorType.VIBRATION, "mm/s", [1.0, 3.0, 6.0, 10.0]),
    }
