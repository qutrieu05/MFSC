"""Decision Engine (Layer 4, IF-06): combine inspection channel(s) into a final verdict.

Depends only on ``msfc.core`` and ``msfc.domain`` — it has no idea MQTT, the Cell
Controller's FIFO, or where an InspectionResult came from (ARCHITECTURE.md section 7.2).
``msfc.sim``/``msfc.services`` own wiring this to a bus and to the vision pipeline.
"""

from __future__ import annotations

from typing import Sequence

from msfc.core.errors import DecisionError
from msfc.core.logging_setup import ctx, get_logger
from msfc.decision.policy import DecisionPolicy
from msfc.domain import DecisionRecord, InspectionResult, RawVerdict, Verdict, VerdictCommand

log = get_logger("msfc.decision")

_MAX_REASON_CODES = 8


class DecisionEngine:
    """Rules: **any DEFECT wins** (fail-closed across channels); otherwise **any UNCERTAIN**
    resolves per :attr:`DecisionPolicy.uncertain_verdict`; otherwise GOOD (FR-DEC-01, 04).
    """

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self._policy = policy or DecisionPolicy()

    @property
    def policy(self) -> DecisionPolicy:
        return self._policy

    def decide(
        self,
        product_id: str,
        inspections: Sequence[InspectionResult],
        *,
        detected_at_mono_ms: int,
        now_mono_ms: int,
    ) -> DecisionRecord:
        """Combine *inspections* (all for the same product) into a :class:`DecisionRecord`.

        Args:
            product_id: must match every ``inspections[i].product_id``.
            inspections: one per inspection channel (today: just vision; OCR joins in
                Phase 3). Must be non-empty — if nothing inspected the product, there is no
                decision to make; the Cell Controller/simulator's own NO_DECISION timeout
                handles that case, not this method.
            detected_at_mono_ms: when the product was detected (Cell Controller clock).
            now_mono_ms: when this decision is being made (same clock) — used only to flag
                ``late`` (FR-DEC-02); the *real* timing enforcement is on the firmware side.

        Raises:
            DecisionError: empty *inspections*, a product_id mismatch, or a clock going
                backwards.
        """
        if not inspections:
            raise DecisionError(f"decide() requires at least one InspectionResult for product {product_id!r}")
        for insp in inspections:
            if insp.product_id != product_id:
                raise DecisionError(
                    f"InspectionResult.product_id {insp.product_id!r} does not match {product_id!r}"
                )
        if now_mono_ms < detected_at_mono_ms:
            raise DecisionError("now_mono_ms must not be before detected_at_mono_ms")

        final_verdict, reason_codes = self._combine(inspections)

        latency_ms = now_mono_ms - detected_at_mono_ms
        late = latency_ms > self._policy.deadline_ms
        if late:
            reason_codes.append("DECISION_LATE")

        record = DecisionRecord(
            decision_id=f"d-{product_id}",
            product_id=product_id,
            final_verdict=final_verdict,
            reason_codes=tuple(reason_codes[:_MAX_REASON_CODES]),
            rules_version=self._policy.rules_version,
            late=late,
            inputs={
                insp.model.name: {"verdict": insp.verdict.value, "confidence": insp.confidence}
                for insp in inspections
            },
        )
        log.info("decision made", extra=ctx(
            product_id=product_id, verdict=final_verdict.value, late=late, latency_ms=latency_ms,
            reason_codes=list(record.reason_codes),
        ))
        return record

    def _combine(self, inspections: Sequence[InspectionResult]) -> tuple[Verdict, list[str]]:
        reason_codes: list[str] = []
        raw_verdicts = [insp.verdict for insp in inspections]

        if RawVerdict.DEFECT in raw_verdicts:
            for insp in inspections:
                if insp.verdict == RawVerdict.DEFECT:
                    reason_codes.append(f"{insp.model.name.upper()}_DEFECT")
            return Verdict.DEFECT, reason_codes

        if RawVerdict.UNCERTAIN in raw_verdicts:
            resolved = Verdict(self._policy.uncertain_verdict.value)
            reason_codes.append(f"UNCERTAIN_POLICY_{resolved.value}")
            for insp in inspections:
                if insp.verdict == RawVerdict.UNCERTAIN:
                    reason_codes.append(f"{insp.model.name.upper()}_UNCERTAIN")
            return resolved, reason_codes

        reason_codes.append("ALL_CHANNELS_GOOD")
        return Verdict.GOOD, reason_codes

    def to_verdict_command(self, record: DecisionRecord, *, confidence: float | None = None) -> VerdictCommand:
        """Build the (advisory) message sent to the Cell Controller (ADR-0005)."""
        return VerdictCommand(
            product_id=record.product_id,
            verdict=record.final_verdict,
            decision_id=record.decision_id,
            reason_codes=record.reason_codes,
            confidence=confidence,
        )
