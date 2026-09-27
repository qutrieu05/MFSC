"""Fault code catalog (SAFETY_CONCEPT.md section 5) — the single source of truth for fault codes.

Firmware and the Edge Server must not invent ad-hoc fault codes: every code raised in the
simulator, decision engine, or (later) real firmware must come from this catalog, so the
catalog, SAFETY_CONCEPT.md and the reset matrix stay in sync. See
``edge/tests/unit/test_faults.py`` for the check that every code used elsewhere is declared
here and that latching matches the severity rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from msfc.core.errors import DomainError
from msfc.domain.enums import FaultSeverity

_CODE_RE = re.compile(r"^[FE][0-9]{3}$")


class UnknownFaultCodeError(DomainError):
    """Raised when code refers to a fault code not present in FAULT_CATALOG."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"unknown fault code {code!r}; add it to msfc.domain.faults.FAULT_CATALOG")


@dataclass(frozen=True, slots=True)
class FaultCode:
    """One entry of the fault code catalog.

    Attributes:
        code: pattern ``[FE][0-9]{3}`` (fault.v1 schema).
        name: short machine-readable name, e.g. ``COMM_LOSS_EDGE``.
        severity: INFO/WARNING/FAULT/SAFETY.
        latching: True if the condition persists until an explicit, controlled reset
            (SAFETY_CONCEPT.md section 4); False if it self-clears once the cause is gone.
        description: one-line human explanation.
    """

    code: str
    name: str
    severity: FaultSeverity
    latching: bool
    description: str

    def __post_init__(self) -> None:
        if not _CODE_RE.match(self.code):
            raise DomainError(f"fault code {self.code!r} does not match [FE][0-9]{{3}}")


def _entry(code: str, name: str, severity: FaultSeverity, latching: bool, description: str) -> FaultCode:
    return FaultCode(code=code, name=name, severity=severity, latching=latching, description=description)


_ENTRIES = (
    _entry("F001", "ESTOP_ACTIVE", FaultSeverity.SAFETY, True,
           "E-stop pressed or input wire cut (SAF-11); hardware channel also cuts motor power directly"),
    _entry("F010", "COMM_LOSS_EDGE", FaultSeverity.FAULT, True,
           "Edge Server heartbeat missing beyond comm.heartbeat_timeout_ms (SF-02)"),
    _entry("F011", "MQTT_DISCONNECTED", FaultSeverity.WARNING, False,
           "Broker connection lost while idle; escalates to F010 if it persists while running"),
    _entry("F020", "ZONE_INTRUSION", FaultSeverity.SAFETY, True,
           "Danger zone occupied (SF-03); requires clear_hold_ms of zone_clear before reset"),
    _entry("F021", "SAFETY_VISION_LOST", FaultSeverity.SAFETY, True,
           "Safety heartbeat stale or frame_seq not increasing (SF-04)"),
    _entry("F030", "TRACKING_MISMATCH", FaultSeverity.FAULT, True,
           "Product FIFO empty at S2, or detected-without-verdict count exceeds policy"),
    _entry("F031", "TRACKING_QUEUE_OVERFLOW", FaultSeverity.FAULT, True,
           "Product tracker FIFO exceeded its configured depth"),
    _entry("F032", "DECISION_LATE", FaultSeverity.WARNING, False,
           "Verdict arrived after the product already reached S2"),
    _entry("F033", "NO_DECISION_REJECT", FaultSeverity.WARNING, False,
           "Product rejected because no verdict arrived in time (counted, not a machine fault)"),
    _entry("F040", "ACTUATOR_FAULT", FaultSeverity.FAULT, True,
           "Pusher did not reach the expected position (requires position feedback; FUTURE)"),
    _entry("F041", "MOTOR_STALL", FaultSeverity.FAULT, True,
           "Motor current/encoder indicates a stall (requires current sensing; Phase 5)"),
    _entry("F050", "SELF_TEST_FAILED", FaultSeverity.FAULT, True,
           "Boot self-test failed (HAL init error)"),
    _entry("F051", "WATCHDOG_RESET", FaultSeverity.WARNING, False,
           "Device rebooted because of a watchdog timeout; informational after boot"),
    _entry("F052", "BROWNOUT_RESET", FaultSeverity.WARNING, False,
           "Device rebooted because of a brownout; informational after boot"),
    _entry("F060", "CONFIG_INVALID", FaultSeverity.FAULT, True,
           "Device configuration failed validation at startup"),
    _entry("F070", "HEALTH_SENSOR_INVALID", FaultSeverity.WARNING, False,
           "A machine-health sensor reading is out of range or stuck (Phase 5)"),
    _entry("E101", "PAYLOAD_INVALID", FaultSeverity.WARNING, False,
           "Incoming MQTT payload failed schema validation (MQTT_CONTRACT.md section 7)"),
    _entry("E102", "SCHEMA_UNSUPPORTED", FaultSeverity.WARNING, False,
           "Envelope names a schema version this receiver does not support"),
    _entry("E103", "TOPIC_UNKNOWN", FaultSeverity.INFO, False,
           "Message arrived on a topic outside the registry"),
)

FAULT_CATALOG: dict[str, FaultCode] = {entry.code: entry for entry in _ENTRIES}


def lookup(code: str) -> FaultCode:
    """Return the catalog entry for *code*, or raise UnknownFaultCodeError."""
    try:
        return FAULT_CATALOG[code]
    except KeyError as exc:
        raise UnknownFaultCodeError(code) from exc
