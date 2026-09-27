"""P6.2/P6.5: per-product pipeline orchestration.

    FrameSource -> Vision -> OCR -> Decision -> Safety Gate -> Cell Command -> Controller

This module is pure with respect to the bus/MQTT: :func:`run_product_cycle` takes a frame and
returns a :class:`~msfc.services.platform_model.ProductCycleTrace`; it never publishes
anything. ``msfc.services.runtime.CellRuntime`` is what wires this to a live
:class:`~msfc.comm.MessageBus` -- keeping the two separate is what makes this function
deterministically unit-testable without any bus/contract machinery, and is itself an instance
of the "avoid coupling to MQTT" rule (P6.2).

Precedence (P6.5), built entirely from decisions that already exist elsewhere rather than a new
hierarchy invented here (per the PO's explicit "use the existing decisions as the source of
truth"):

    1. Safety gate (this cell's last known MachineState is latched, or unknown) -> SAFETY_DENIED.
       Nothing below runs. (msfc.services.safety_gate; ultimately enforced by the Cell
       Controller itself regardless of this check -- see that module's docstring.)
    2. Vision channel: try it; a missing frame or a raised exception is ONE MISSING CHANNEL,
       never a fabricated GOOD (P6.10). Vision producing an ambiguous *scored* result is not a
       failure -- msfc.vision.postprocess already resolves that to RawVerdict.UNCERTAIN, which
       flows into step 4 completely normally.
    3. OCR channel: msfc.ocr.pipeline.run_ocr_pipeline already never raises for a *content*
       problem (bad label, unreadable, expired) -- it always returns a classified
       InspectionResult (already fail-closed, D-043/P3.12, unchanged). Only a real
       misconfiguration (OcrError) is treated as a missing channel here.
    4. If no channel produced a result -> NO_DECISION: no verdict is published. This is not a
       new fail-closed rule -- it reuses ADR-0005/ARCHITECTURE.md principle P3, "no verdict =
       reject", already fully implemented and tested in msfc.sim.SimCellController's own
       no-verdict timeout (test_pipeline_mvp_fails_closed_when_no_verdict_arrives_in_time).
    5. Otherwise: msfc.decision.DecisionEngine.decide() on whatever channels ARE present -- its
       own "any DEFECT wins, then UNCERTAIN per policy, then GOOD" rule is unchanged and is
       exactly where "Vision/OCR uncertainty > Normal production decision" is already enforced
       (DecisionPolicy.uncertain_verdict defaults to DEFECT, FR-DEC-04).

Machine-health CRITICAL is deliberately NOT part of this precedence chain: D-054 (DECISIONS.md,
Phase 5) already established that a health event is observational, never a safety/production
gate, and nothing in this module's non-negotiable rules permits changing that here. A health
CRITICAL is observed and optionally bridged into OEE (msfc.services.health_pipeline) entirely
independently of whether any given product is accepted or rejected.
"""

from __future__ import annotations

from dataclasses import dataclass

from msfc.core.errors import OcrError
from msfc.core.logging_setup import ctx, get_logger
from msfc.decision import DecisionEngine
from msfc.domain import CellStateSnapshot, InspectionResult, ModelInfo
from msfc.ocr import LabelValidationConfig, OcrEngine, PreprocessConfig, run_ocr_pipeline
from msfc.services.platform_model import PipelineOutcome, ProductCycleTrace
from msfc.services.safety_gate import evaluate_safety_gate
from msfc.services.timing import StageTimer
from msfc.services.vision_pipeline import run_vision_pipeline
from msfc.vision import Frame, InferenceEngine, RoiConfig, Thresholds

log = get_logger("msfc.services.pipeline")


@dataclass(frozen=True, slots=True)
class VisionStageConfig:
    engine: InferenceEngine
    roi: RoiConfig
    thresholds: Thresholds
    model: ModelInfo


@dataclass(frozen=True, slots=True)
class OcrStageConfig:
    engine: OcrEngine
    preprocess: PreprocessConfig
    label_config: LabelValidationConfig
    reference_date: object  # datetime.date; kept loosely typed to avoid importing datetime here for a type-only use


def run_product_cycle(
    product_id: str,
    *,
    frame: Frame | None,
    cell_state: CellStateSnapshot | None,
    vision: VisionStageConfig | None,
    ocr: OcrStageConfig | None,
    decision_engine: DecisionEngine,
    detected_at_mono_ms: int,
    now_mono_ms: int,
    timer: StageTimer | None = None,
) -> tuple[ProductCycleTrace, tuple[str, ...]]:
    """Run one product through the pipeline. Returns ``(trace, failed_subsystems)`` --
    ``failed_subsystems`` names each configured channel that raised an unexpected exception
    this cycle (for the caller's degraded-mode bookkeeping, P6.10/P6.11); it is empty on a
    clean run, including a clean SAFETY_DENIED/NO_DECISION outcome."""
    failed: list[str] = []

    gate = evaluate_safety_gate(cell_state)
    if not gate.allowed:
        log.info("safety gate denied product", extra=ctx(product_id=product_id, reason=gate.reason))
        trace = ProductCycleTrace(
            product_id=product_id, outcome=PipelineOutcome.SAFETY_DENIED,
            detected_at_mono_ms=detected_at_mono_ms, decided_at_mono_ms=now_mono_ms,
            denial_reason=gate.reason,
        )
        return trace, ()

    inspection: InspectionResult | None = None
    if vision is not None and frame is not None:
        try:
            with (timer.stage("vision") if timer is not None else _noop_cm()):
                inspection = run_vision_pipeline(
                    frame, engine=vision.engine, roi=vision.roi, thresholds=vision.thresholds,
                    model=vision.model, product_id=product_id,
                )
        except Exception as exc:  # deliberately broad: any vision failure (bad ROI, engine
            # crash, unexpected bug) means "no vision channel this cycle," never a silently
            # fabricated verdict (P6.10).
            log.warning("vision channel unavailable this cycle", extra=ctx(product_id=product_id, error=str(exc)))
            failed.append("vision")

    label: InspectionResult | None = None
    if ocr is not None and frame is not None:
        try:
            with (timer.stage("ocr") if timer is not None else _noop_cm()):
                label = run_ocr_pipeline(
                    frame.image, engine=ocr.engine, preprocess_config=ocr.preprocess,
                    label_config=ocr.label_config, reference_date=ocr.reference_date,
                    product_id=product_id, frame_seq=frame.seq,
                )
        except OcrError as exc:
            # A genuine misconfiguration (bad ROI/config), not a content problem -- content
            # problems already resolve inside run_ocr_pipeline without raising (D-043/P3.12).
            log.warning("OCR channel unavailable this cycle", extra=ctx(product_id=product_id, error=str(exc)))
            failed.append("ocr")

    channels = [c for c in (inspection, label) if c is not None]
    if not channels:
        log.info("no inspection channel available; no verdict will be published (fail-closed)",
                  extra=ctx(product_id=product_id))
        trace = ProductCycleTrace(
            product_id=product_id, outcome=PipelineOutcome.NO_DECISION,
            detected_at_mono_ms=detected_at_mono_ms, decided_at_mono_ms=now_mono_ms,
            inspection=inspection, label=label,
        )
        return trace, tuple(failed)

    with (timer.stage("decision") if timer is not None else _noop_cm()):
        record = decision_engine.decide(product_id, channels, detected_at_mono_ms=detected_at_mono_ms,
                                         now_mono_ms=now_mono_ms)
    confidence = channels[0].confidence if len(channels) == 1 else None
    verdict_command = decision_engine.to_verdict_command(record, confidence=confidence)

    trace = ProductCycleTrace(
        product_id=product_id,
        outcome=PipelineOutcome.GOOD if record.final_verdict.value == "GOOD" else PipelineOutcome.DEFECT,
        detected_at_mono_ms=detected_at_mono_ms, decided_at_mono_ms=now_mono_ms,
        inspection=inspection, label=label, decision=record, verdict_command=verdict_command,
    )
    return trace, tuple(failed)


class _noop_cm:
    """A do-nothing context manager, used when the caller passes no :class:`StageTimer`."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc_info: object) -> bool:
        return False


__all__ = ["VisionStageConfig", "OcrStageConfig", "run_product_cycle"]
