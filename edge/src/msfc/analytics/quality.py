"""Sensor data-quality validation (P5.3) — deterministic, one quality tag per measurement.

Priority order when multiple problems apply at once (most certain/severe first): MISSING ->
INVALID_UNIT -> INVALID (NaN/Inf/impossible value) -> FUTURE_TIMESTAMP -> DUPLICATE -> STALE ->
OK. Never returns OK for a value that failed any check — P5.3: "do not silently convert bad
sensor data into valid health data."
"""

from __future__ import annotations

import math

from dataclasses import dataclass

from msfc.core.errors import HealthError
from msfc.analytics.health_models import SensorMeasurement, SensorQuality, SensorType


@dataclass(frozen=True, slots=True)
class QualityConfig:
    expected_unit: str
    valid_range: tuple[float, float] | None = None  # physically-impossible bounds, e.g. (-50, 300) degC
    stale_after_ms: int = 60_000
    max_future_skew_ms: int = 1_000

    def __post_init__(self) -> None:
        if self.stale_after_ms <= 0:
            raise HealthError(f"stale_after_ms must be > 0, got {self.stale_after_ms!r}")
        if self.max_future_skew_ms < 0:
            raise HealthError(f"max_future_skew_ms must be >= 0, got {self.max_future_skew_ms!r}")
        if self.valid_range is not None and self.valid_range[0] > self.valid_range[1]:
            raise HealthError(f"valid_range must be (low, high) with low <= high, got {self.valid_range!r}")


def assess_quality(*, value: float | None, unit: str, mono_ms: int, now_mono_ms: int,
                    config: QualityConfig, last_mono_ms: int | None = None) -> SensorQuality:
    if value is None:
        return SensorQuality.MISSING
    if unit != config.expected_unit:
        return SensorQuality.INVALID_UNIT
    if math.isnan(value) or math.isinf(value):
        return SensorQuality.INVALID
    if config.valid_range is not None:
        low, high = config.valid_range
        if not (low <= value <= high):
            return SensorQuality.INVALID
    if mono_ms > now_mono_ms + config.max_future_skew_ms:
        return SensorQuality.FUTURE_TIMESTAMP
    if last_mono_ms is not None and mono_ms == last_mono_ms:
        return SensorQuality.DUPLICATE
    if now_mono_ms - mono_ms > config.stale_after_ms:
        return SensorQuality.STALE
    return SensorQuality.OK


def build_measurement(
    *, sensor_id: str, sensor_type: SensorType, value: float | None, unit: str, mono_ms: int,
    now_mono_ms: int, config: QualityConfig, last_mono_ms: int | None = None,
) -> SensorMeasurement:
    """Always returns a :class:`SensorMeasurement` (never raises for bad *content* — a
    malformed reading is itself a valid, reportable fact) with an honest quality tag. A
    missing/invalid value is recorded as ``0.0`` with the corresponding quality flag; callers
    (feature extraction, anomaly detection) must check ``quality`` before trusting ``value``."""
    quality = assess_quality(value=value, unit=unit, mono_ms=mono_ms, now_mono_ms=now_mono_ms,
                              config=config, last_mono_ms=last_mono_ms)
    safe_value = value if (value is not None and not math.isnan(value) and not math.isinf(value)) else 0.0
    return SensorMeasurement(sensor_id=sensor_id, sensor_type=sensor_type, mono_ms=mono_ms,
                              value=safe_value, unit=unit, quality=quality)
