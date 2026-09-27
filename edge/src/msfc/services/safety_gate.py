"""P6.4/P6.5: the orchestration-level safety gate.

CRITICAL, read this before changing anything here: this module is NOT the safety authority.
The Cell Controller (real firmware, or ``msfc.sim.SimCellController`` standing in for it) is
and remains the *sole* safety authority (P2, unmodified) -- it independently rejects any
command with an explicit :class:`~msfc.domain.enums.RejectReason` regardless of what this
module decides, and it does so even if ``msfc.services`` never existed at all. This gate is a
courtesy, defense-in-depth check so the orchestrator does not waste a vision/OCR/decision cycle
-- and does not confusingly publish a verdict -- for a product that arrived while the cell is
already latched. Removing this module would make the platform slower and noisier, never less
safe, because the real enforcement lives elsewhere.

Fail-closed default (P6.10 "Unknown should remain UNKNOWN where uncertainty cannot legitimately
be resolved"): if the cell's state has never been observed yet, the gate denies -- it never
assumes "probably fine" just because nothing bad has been reported.
"""

from __future__ import annotations

from dataclasses import dataclass

from msfc.domain import LATCHED_STATES, CellStateSnapshot


@dataclass(frozen=True, slots=True)
class SafetyGateResult:
    allowed: bool
    reason: str | None = None


def evaluate_safety_gate(cell_state: CellStateSnapshot | None) -> SafetyGateResult:
    """Whether ``msfc.services`` should even attempt to produce a verdict for a newly detected
    product, given the last known :class:`CellStateSnapshot`."""
    if cell_state is None:
        return SafetyGateResult(allowed=False, reason="CELL_STATE_UNKNOWN")
    if cell_state.machine_state in LATCHED_STATES:
        return SafetyGateResult(allowed=False, reason=f"CELL_LATCHED_{cell_state.machine_state.value}")
    return SafetyGateResult(allowed=True)


__all__ = ["SafetyGateResult", "evaluate_safety_gate"]
