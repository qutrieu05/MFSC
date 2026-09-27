"""Commands and acknowledgements exchanged with the Cell Controller.

Mirrors verdict_cmd.v1, control_cmd.v1 and cmd_ack.v1. See MQTT_CONTRACT.md section 5 for
the acknowledgement protocol these types encode.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from msfc.core.errors import DomainError
from msfc.domain import _validators as v
from msfc.domain.enums import CommandAction, CommandResult, MachineState, Verdict


@dataclass(frozen=True, slots=True)
class VerdictCommand:
    """Decision Engine -> Cell Controller: the advisory verdict for one product (ADR-0005).

    This is advisory: the Cell Controller owns timing and will reject the product if this
    never arrives (or arrives late) — see ``msfc.sim`` and ARCHITECTURE.md section 5.1.
    """

    product_id: str
    verdict: Verdict
    decision_id: str
    reason_codes: tuple[str, ...]
    confidence: float | None = None

    def __post_init__(self) -> None:
        v.product_id(self.product_id)
        v.non_empty_str(self.decision_id, field="decision_id", max_len=40)
        if not self.reason_codes or len(self.reason_codes) > 8:
            raise DomainError("reason_codes must have 1 to 8 entries")
        if self.confidence is not None:
            v.unit_interval(self.confidence, field="confidence")


@dataclass(frozen=True, slots=True)
class ControlCommand:
    """Operator/control command to the Cell Controller (control_cmd.v1)."""

    cmd_id: str
    action: CommandAction
    source: str
    params: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        v.non_empty_str(self.cmd_id, field="cmd_id", max_len=40)
        v.non_empty_str(self.source, field="source", max_len=60)
        if self.action == CommandAction.SET_SPEED:
            if "speed_pct" not in self.params:
                raise DomainError("set_speed command requires params['speed_pct']")
            pct = self.params["speed_pct"]
            if not (0.0 <= pct <= 100.0):
                raise DomainError(f"speed_pct must be in [0, 100], got {pct!r}")


@dataclass(frozen=True, slots=True)
class CommandAck:
    """Cell Controller -> sender: outcome of a ControlCommand (cmd_ack.v1)."""

    cmd_id: str
    action: str
    result: CommandResult
    reason: str | None = None
    state_after: MachineState | None = None

    def __post_init__(self) -> None:
        v.non_empty_str(self.cmd_id, field="cmd_id", max_len=40)
        v.non_empty_str(self.action, field="action", max_len=40)
        if self.result in (CommandResult.REJECTED, CommandResult.FAILED) and not self.reason:
            raise DomainError(f"result={self.result.value} requires a 'reason' (MQTT_CONTRACT.md section 5)")
