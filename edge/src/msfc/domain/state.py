"""Cell Controller state snapshot and fault reports.

Mirrors cell_state.v1 and fault.v1. ``CellStateSnapshot`` is what gets published (retained)
on ``conveyor/{device}/state``; it is also exactly what ``msfc.sim`` exposes so tests can
assert on simulated hardware behaviour (motor, pusher, safety relay) without any MQTT layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from msfc.core.errors import DomainError
from msfc.domain.enums import NON_PRODUCTION_STATES, MachineState, PusherState
from msfc.domain.faults import FaultCode


@dataclass(frozen=True, slots=True)
class Counters:
    """Production counters (cell_state.v1 'counters')."""

    detected: int = 0
    passed: int = 0
    rejected: int = 0
    no_decision: int = 0

    def __post_init__(self) -> None:
        for name in ("detected", "passed", "rejected", "no_decision"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise DomainError(f"counters.{name} must be a non-negative integer, got {value!r}")

    def with_detected(self) -> "Counters":
        return replace(self, detected=self.detected + 1)

    def with_passed(self) -> "Counters":
        return replace(self, passed=self.passed + 1)

    def with_rejected(self, *, no_decision: bool) -> "Counters":
        if no_decision:
            return replace(self, rejected=self.rejected + 1, no_decision=self.no_decision + 1)
        return replace(self, rejected=self.rejected + 1)


@dataclass(frozen=True, slots=True)
class CellStateSnapshot:
    """Full state snapshot of one Cell Controller (cell_state.v1).

    ``active_faults`` holds fault *codes* (e.g. ``("F001",)``); look them up in
    :data:`msfc.domain.faults.FAULT_CATALOG` for name/severity.
    """

    machine_state: MachineState
    active_faults: tuple[str, ...] = ()
    speed_setpoint_pct: float = 0.0
    motor_output_pct: float = 0.0
    safety_relay_closed: bool = False
    pusher: PusherState = PusherState.RETRACTED
    queue_len: int = 0
    safety_vision_required: bool = False
    counters: Counters = field(default_factory=Counters)

    def __post_init__(self) -> None:
        if not (0.0 <= self.speed_setpoint_pct <= 100.0):
            raise DomainError(f"speed_setpoint_pct must be in [0, 100], got {self.speed_setpoint_pct!r}")
        if not (0.0 <= self.motor_output_pct <= 100.0):
            raise DomainError(f"motor_output_pct must be in [0, 100], got {self.motor_output_pct!r}")
        if self.queue_len < 0:
            raise DomainError(f"queue_len must be >= 0, got {self.queue_len!r}")
        # SAF-10 / SF-07 as a data-level invariant: outside STARTING/RUNNING/STOPPING the
        # relay is open, the motor is off and the pusher is retracted (ARCHITECTURE.md
        # section 4). This is the same rule the firmware (real or simulated) must enforce in
        # hardware; encoding it here means every test that builds a snapshot for a
        # non-production state gets it checked for free.
        if self.machine_state in NON_PRODUCTION_STATES:
            if self.safety_relay_closed:
                raise DomainError(
                    f"safety_relay_closed must be False in {self.machine_state.value} (SAF-10)"
                )
            if self.pusher != PusherState.RETRACTED:
                raise DomainError(
                    f"pusher must be RETRACTED in {self.machine_state.value} (SF-07), got {self.pusher.value}"
                )


@dataclass(frozen=True, slots=True)
class FaultReport:
    """One raise/clear event for a fault (fault.v1)."""

    fault: FaultCode
    event: str  # FaultLifecycleEvent value, kept as str to avoid an import cycle with enums here
    detail: str = ""

    def __post_init__(self) -> None:
        if self.event not in ("RAISED", "CLEARED"):
            raise DomainError(f"event must be 'RAISED' or 'CLEARED', got {self.event!r}")
        if len(self.detail) > 120:
            raise DomainError("detail must be at most 120 characters")
