"""Decision policy: the tunable part of FR-DEC-01..04, kept separate from the engine logic
so a policy change is a config change, not a code change (CODING_STANDARDS.md rule G4).
"""

from __future__ import annotations

from dataclasses import dataclass

from msfc.core.errors import DecisionError
from msfc.domain import RawVerdict


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """
    Attributes:
        uncertain_verdict: what an UNCERTAIN inspection channel resolves to when no channel
            reported DEFECT (FR-DEC-04 default is DEFECT: "when in doubt, reject").
        deadline_ms: used only to flag a decision as ``late`` (FR-DEC-02) for observability;
            the Cell Controller — not this policy — is what actually rejects a product with
            no verdict in time (ADR-0005). Align this with NFR-PERF-01's target (300 ms).
        rules_version: stamped onto every DecisionRecord (FR-DEC-03) so a later change in
            policy is visible in historical decisions rather than silently reinterpreted.
    """

    uncertain_verdict: RawVerdict = RawVerdict.DEFECT
    deadline_ms: int = 300
    rules_version: str = "rules-0.1"

    def __post_init__(self) -> None:
        if self.uncertain_verdict not in (RawVerdict.GOOD, RawVerdict.DEFECT):
            raise DecisionError(
                f"uncertain_verdict must resolve to GOOD or DEFECT, got {self.uncertain_verdict!r}"
            )
        if self.deadline_ms <= 0:
            raise DecisionError(f"deadline_ms must be > 0, got {self.deadline_ms!r}")
        if not self.rules_version.strip():
            raise DecisionError("rules_version must not be empty")
