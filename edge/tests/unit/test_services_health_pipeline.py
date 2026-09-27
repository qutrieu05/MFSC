"""P6.2/P6.11: sensor -> MachineHealthMonitor -> (opt-in) OEE bridge composition tests."""

from __future__ import annotations

from msfc.analytics import (
    AnomalyThresholds,
    HealthBaseline,
    HealthEvent,
    HealthEventType,
    MachineHealthMonitor,
    SensorMeasurement,
    SensorQuality,
    SensorType,
)
from msfc.services.health_pipeline import bridge_critical_events, ingest_sensors


class _FixedReadingSensor:
    def __init__(self, sensor_id: str, sensor_type: SensorType, value: float) -> None:
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self._value = value

    def read(self, *, mono_ms: int) -> SensorMeasurement:
        return SensorMeasurement(sensor_id=self.sensor_id, sensor_type=self.sensor_type,
                                  mono_ms=mono_ms, value=self._value, unit="degC")


class _CrashingSensor:
    sensor_id = "temp-broken"
    sensor_type = SensorType.TEMPERATURE

    def read(self, *, mono_ms: int):
        raise RuntimeError("ADC read failed")


def _monitor() -> MachineHealthMonitor:
    return MachineHealthMonitor(
        baselines={"temp-1": HealthBaseline(sensor_type=SensorType.TEMPERATURE, expected_min=20.0, expected_max=40.0)},
        thresholds={"temp-1": AnomalyThresholds(warning_deviation=2.0, anomaly_deviation=5.0, critical_deviation=10.0)},
        window_ms=5000,
    )


def test_ingest_sensors_feeds_measurements_into_the_monitor() -> None:
    monitor = _monitor()
    sensor = _FixedReadingSensor("temp-1", SensorType.TEMPERATURE, 25.0)
    events, failed = ingest_sensors([sensor], monitor, mono_ms=1000)
    assert failed == ()
    assert any(e.type == HealthEventType.SENSOR_READING for e in events)
    snap = monitor.snapshot(mono_ms=1000)
    assert snap.latest_measurements["temp-1"].value == 25.0


def test_ingest_sensors_detects_a_critical_spike() -> None:
    monitor = _monitor()
    sensor = _FixedReadingSensor("temp-1", SensorType.TEMPERATURE, 55.0)  # 15 above expected_max -> CRITICAL
    events, failed = ingest_sensors([sensor], monitor, mono_ms=1000)
    assert failed == ()
    assert monitor.snapshot(mono_ms=1000).health_state.value == "CRITICAL"
    assert any(e.type == HealthEventType.MACHINE_HEALTH_CRITICAL for e in events)


def test_ingest_sensors_skips_a_failing_sensor_without_faking_a_value() -> None:
    monitor = _monitor()
    events, failed = ingest_sensors([_CrashingSensor()], monitor, mono_ms=1000)
    assert failed == ("temp-broken",)
    assert "temp-broken" not in monitor.snapshot(mono_ms=1000).latest_measurements
    assert monitor.snapshot(mono_ms=1000).health_state.value == "UNKNOWN"


def test_bridge_critical_events_only_bridges_critical() -> None:
    events = (
        HealthEvent(type=HealthEventType.MACHINE_HEALTH_WARNING, mono_ms=1000, sensor_id="temp-1"),
        HealthEvent(type=HealthEventType.MACHINE_HEALTH_CRITICAL, mono_ms=1000, sensor_id="temp-1",
                    detail={"reason": "over_range"}),
    )
    bridged = bridge_critical_events(events)
    assert len(bridged) == 1
    assert bridged[0].detail["fault_code"] == "F070"


def test_bridge_critical_events_returns_empty_for_no_critical_events() -> None:
    events = (HealthEvent(type=HealthEventType.SENSOR_READING, mono_ms=1000, sensor_id="temp-1"),)
    assert bridge_critical_events(events) == ()
