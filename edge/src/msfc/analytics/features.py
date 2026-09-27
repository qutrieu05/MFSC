"""Feature extraction (P5.4) — modular, independent of any ML library (plain statistics only).

Only OK-quality measurements are ever included in a statistic (P5.3 discipline carried
through: a MISSING/INVALID/STALE reading must not silently pull an average toward a fake
value). An empty or all-bad window deterministically returns a :class:`FeatureSet` with
``sample_count=0`` and every statistic ``None`` — not zero, not a crash (P5.15: "empty sensor
stream").
"""

from __future__ import annotations

import math
import statistics
from typing import Sequence

from msfc.core.errors import HealthError
from msfc.analytics.health_models import FeatureSet, SensorMeasurement, SensorQuality, SensorType


def extract_features(
    measurements: Sequence[SensorMeasurement],
    *,
    sensor_id: str,
    sensor_type: SensorType,
    window_start_mono_ms: int,
    window_end_mono_ms: int,
    moving_average_window: int = 5,
) -> FeatureSet:
    if window_end_mono_ms < window_start_mono_ms:
        raise HealthError("window_end_mono_ms must not be before window_start_mono_ms")
    if moving_average_window <= 0:
        raise HealthError(f"moving_average_window must be > 0, got {moving_average_window!r}")

    ok = sorted((m for m in measurements if m.quality is SensorQuality.OK), key=lambda m: m.mono_ms)
    if not ok:
        return FeatureSet(sensor_id=sensor_id, sensor_type=sensor_type,
                           window_start_mono_ms=window_start_mono_ms, window_end_mono_ms=window_end_mono_ms,
                           sample_count=0)

    values = [m.value for m in ok]
    minimum, maximum = min(values), max(values)
    mean = statistics.fmean(values)
    median = statistics.median(values)
    std_dev = statistics.pstdev(values) if len(values) > 1 else 0.0  # a single sample has zero spread
    variance = std_dev * std_dev

    rate_of_change = None
    dt = ok[-1].mono_ms - ok[0].mono_ms
    if len(ok) >= 2 and dt > 0:
        rate_of_change = (ok[-1].value - ok[0].value) / dt

    moving_average = statistics.fmean(values[-moving_average_window:])

    rms = math.sqrt(statistics.fmean(v * v for v in values)) if sensor_type is SensorType.VIBRATION else None

    return FeatureSet(
        sensor_id=sensor_id, sensor_type=sensor_type, window_start_mono_ms=window_start_mono_ms,
        window_end_mono_ms=window_end_mono_ms, sample_count=len(ok), minimum=minimum, maximum=maximum,
        mean=mean, median=median, std_dev=std_dev, variance=variance, value_range=maximum - minimum,
        rate_of_change=rate_of_change, moving_average=moving_average, rms=rms,
    )
