"""Sensor history persistence abstraction (P5.19) — interface + in-memory implementation only,
same pattern and same reasoning as msfc.analytics.repository (P4.17, D-050): this stays inside
msfc.analytics rather than msfc.storage because the layer rules don't let this package depend
on storage; a real backend (SQLite/time-series DB) belongs there, wired in by msfc.services.
"""

from __future__ import annotations

from typing import Protocol

from msfc.analytics.health_models import SensorMeasurement


class SensorHistoryRepository(Protocol):
    def save(self, measurement: SensorMeasurement) -> None: ...
    def history(self, sensor_id: str) -> tuple[SensorMeasurement, ...]: ...
    def latest(self, sensor_id: str) -> SensorMeasurement | None: ...


class InMemorySensorHistoryRepository:
    def __init__(self) -> None:
        self._by_sensor: dict[str, list[SensorMeasurement]] = {}

    def save(self, measurement: SensorMeasurement) -> None:
        self._by_sensor.setdefault(measurement.sensor_id, []).append(measurement)

    def history(self, sensor_id: str) -> tuple[SensorMeasurement, ...]:
        return tuple(self._by_sensor.get(sensor_id, ()))

    def latest(self, sensor_id: str) -> SensorMeasurement | None:
        entries = self._by_sensor.get(sensor_id)
        return entries[-1] if entries else None
