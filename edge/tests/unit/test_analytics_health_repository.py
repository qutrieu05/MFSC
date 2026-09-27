"""P5.19 sensor history persistence abstraction — interface + in-memory only."""

from __future__ import annotations

from msfc.analytics.health_models import SensorMeasurement, SensorType
from msfc.analytics.health_repository import InMemorySensorHistoryRepository, SensorHistoryRepository

_M1 = SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=0, value=70.0, unit="degC")
_M2 = SensorMeasurement(sensor_id="temp01", sensor_type=SensorType.TEMPERATURE, mono_ms=1000, value=71.0, unit="degC")


def test_in_memory_repository_satisfies_the_protocol() -> None:
    repo: SensorHistoryRepository = InMemorySensorHistoryRepository()
    assert isinstance(repo, InMemorySensorHistoryRepository)


def test_latest_is_none_for_unknown_sensor() -> None:
    repo = InMemorySensorHistoryRepository()
    assert repo.latest("unknown") is None
    assert repo.history("unknown") == ()


def test_save_and_latest() -> None:
    repo = InMemorySensorHistoryRepository()
    repo.save(_M1)
    repo.save(_M2)
    assert repo.latest("temp01") is _M2


def test_history_preserves_insertion_order() -> None:
    repo = InMemorySensorHistoryRepository()
    repo.save(_M1)
    repo.save(_M2)
    assert repo.history("temp01") == (_M1, _M2)


def test_sensors_are_isolated() -> None:
    other = SensorMeasurement(sensor_id="current01", sensor_type=SensorType.CURRENT, mono_ms=0, value=2.0, unit="A")
    repo = InMemorySensorHistoryRepository()
    repo.save(_M1)
    repo.save(other)
    assert repo.history("temp01") == (_M1,)
    assert repo.history("current01") == (other,)
