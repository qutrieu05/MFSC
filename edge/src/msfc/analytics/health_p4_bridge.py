"""P5.16/P5.17: how (if at all) a machine-health event becomes visible to P4's OEE/downtime
tracking.

P5.17 explicitly warns against automatically classifying every anomaly as downtime, and asks
for the distinction between HEALTH ANOMALY, MACHINE FAULT, DOWNTIME, and EMERGENCY STOP to be
documented (D-054, DECISIONS.md):

    HEALTH ANOMALY  -- msfc.analytics.health_models.HealthEvent (WARNING/ANOMALY/CRITICAL
                        state). Purely informational by default. Production continues.
    MACHINE FAULT    -- msfc.domain fault codes (F0xx), owned by firmware/msfc.sim (P1/P2).
                        A health CRITICAL does NOT, by itself, raise a domain fault -- there is
                        no code path from this module into msfc.sim or the firmware (the layer
                        rules make that import impossible in the first place).
    DOWNTIME         -- msfc.analytics.events.MachineEventType.DOWNTIME_START/END, derived
                        from actual MachineState transitions (P4), never from a health event.
    EMERGENCY STOP   -- msfc.analytics.events.MachineEventType.EMERGENCY_STOP, derived from an
                        actual ESTOP state transition (P2/P1), never triggered by this module.

This module provides exactly ONE, OPT-IN bridge: converting a MACHINE_HEALTH_CRITICAL health
event into a P4 MachineEvent of type FAULT, so a critical health condition is at least visible
in OEE reporting as a fault marker -- a caller (a future msfc.services) decides whether to call
this at all; nothing in msfc.analytics wires it in automatically. WARNING/ANOMALY health states
never produce a MachineEvent through this bridge, matching "warning without downtime" and
"anomaly with continued production" from the PO's examples. Turning a health event into an
actual MachineState transition (and therefore real downtime/E-STOP) remains exclusively P1/P2's
job -- this bridge only ever produces an OBSERVATIONAL FAULT marker for OEE, never a command.
"""

from __future__ import annotations

from msfc.analytics.events import MachineEvent, MachineEventType
from msfc.analytics.health_models import HealthEvent, HealthEventType


def bridge_critical_health_to_machine_event(health_event: HealthEvent) -> MachineEvent | None:
    """Returns a P4 ``MachineEvent`` (type FAULT) only for MACHINE_HEALTH_CRITICAL; None for
    every other health event type (P5.17: not every anomaly becomes downtime)."""
    if health_event.type is not HealthEventType.MACHINE_HEALTH_CRITICAL:
        return None
    return MachineEvent(
        MachineEventType.FAULT, health_event.mono_ms,
        detail={"fault_code": "F070", "source": "health", "sensor_id": health_event.sensor_id,
                "detail": health_event.detail},
    )
