"""Sensor abstraction (P5.2) — mirrors msfc.ocr.engine.OcrEngine / msfc.vision.InferenceEngine's
shape: same Protocol -> Mock -> future real backend pattern already proven twice in this
codebase, reused rather than reinvented (P5's "inspect P1/P3/P4, reuse compatible concepts").

    Mock Sensor -> SensorSource -> health pipeline           (today)
    Real Sensor / ESP32 / PLC -> same SensorSource -> ...    (later, no rewrite needed)
"""

from __future__ import annotations

from typing import Protocol

from msfc.analytics.health_models import SensorMeasurement, SensorQuality, SensorType


class SensorSource(Protocol):
    """A source of measurements for one sensor. Real implementations (ESP32 ADC read, PLC
    telemetry poll, etc.) plug in here without the rest of msfc.analytics changing."""

    sensor_id: str
    sensor_type: SensorType

    def read(self, *, mono_ms: int) -> SensorMeasurement: ...


class FixedSequenceSensorSource:
    """Deterministic test/mock sensor (P5.2's "Mock Sensor") — replays a pre-built sequence of
    measurements in order, one per call to :meth:`read`, regardless of the requested
    ``mono_ms`` (the caller controls timing; this source only controls values). Driven the
    same way :class:`msfc.ocr.engine.FixtureOcrEngine` and
    ``tests/integration/test_full_pipeline_mvp.py``'s ``_OracleVisionEngine`` are: explicit,
    not identity- or clock-based.
    """

    def __init__(self, sensor_id: str, sensor_type: SensorType, measurements: list[SensorMeasurement]) -> None:
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self._measurements = list(measurements)
        self._index = 0

    def read(self, *, mono_ms: int) -> SensorMeasurement:
        if self._index >= len(self._measurements):
            return SensorMeasurement(sensor_id=self.sensor_id, sensor_type=self.sensor_type,
                                      mono_ms=mono_ms, value=0.0, unit="", quality=SensorQuality.UNAVAILABLE)
        measurement = self._measurements[self._index]
        self._index += 1
        return measurement

    def remaining(self) -> int:
        return len(self._measurements) - self._index
