"""P6.2/P6.11: wires sensor sources into ``msfc.analytics``'s machine-health monitor.

    Sensors -> MachineHealthMonitor -> HealthEvent stream -> (optional, opt-in) bridge -> OEE

Mirrors ``msfc.services.pipeline`` in spirit: pure composition of existing P5 building blocks
(``msfc.analytics.MachineHealthMonitor``, ``msfc.analytics.bridge_critical_health_to_machine_event``),
no new health logic. The bridge stays opt-in here exactly as D-054 (DECISIONS.md) requires --
``bridge_critical=False`` by default, and even when enabled it only ever turns
MACHINE_HEALTH_CRITICAL into an observational OEE fault marker, never a command, never a
MachineState change (msfc.services cannot import msfc.sim/firmware at all, so it is
architecturally incapable of doing so even if it wanted to).

P6.11's degraded-mode rule this module exists to satisfy: "machine-health analytics unavailable
should not silently claim HEALTHY." If a sensor read raises, this module does NOT feed a
fabricated OK measurement into the monitor -- it skips that sensor for this tick and reports
the failure to the caller, leaving the monitor's own state exactly where quality-tagged data
already left it (HealthState.UNKNOWN until real data arrives, per msfc.analytics, unchanged).
"""

from __future__ import annotations

from msfc.analytics import HealthEvent, MachineEvent, MachineHealthMonitor, SensorSource, bridge_critical_health_to_machine_event
from msfc.core.logging_setup import ctx, get_logger

log = get_logger("msfc.services.health_pipeline")


def ingest_sensors(
    sensors: list[SensorSource],
    monitor: MachineHealthMonitor,
    *,
    mono_ms: int,
) -> tuple[tuple[HealthEvent, ...], tuple[str, ...]]:
    """Read every sensor once and feed it to *monitor*. Returns
    ``(new_health_events, failed_sensor_ids)`` -- a sensor whose ``.read()`` raises is skipped
    (never fed a fake value) and named in ``failed_sensor_ids`` for the caller's degraded-mode
    bookkeeping."""
    failed: list[str] = []
    for sensor in sensors:
        try:
            measurement = sensor.read(mono_ms=mono_ms)
        except Exception as exc:
            log.warning("sensor unavailable this tick", extra=ctx(sensor_id=sensor.sensor_id, error=str(exc)))
            failed.append(sensor.sensor_id)
            continue
        monitor.ingest(measurement, mono_ms=mono_ms)
    return monitor.drain_events(), tuple(failed)


def bridge_critical_events(events: tuple[HealthEvent, ...]) -> tuple[MachineEvent, ...]:
    """Opt-in (P5.17/D-054): convert only MACHINE_HEALTH_CRITICAL events into observational P4
    MachineEvents. The caller decides whether to feed the result into a
    :class:`~msfc.analytics.MachineMonitor` at all -- this function never does so itself."""
    bridged = (bridge_critical_health_to_machine_event(e) for e in events)
    return tuple(e for e in bridged if e is not None)


__all__ = ["ingest_sensors", "bridge_critical_events"]
