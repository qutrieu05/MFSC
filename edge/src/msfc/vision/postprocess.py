"""Postprocessing: raw class scores -> a domain InspectionResult (FR-VIS-05).

The UNCERTAIN band exists so a score sitting right on the threshold is reported honestly
rather than forced to a coin-flip GOOD/DEFECT; msfc.decision (not this module) decides what
to *do* with UNCERTAIN (FR-DEC-04's default policy is "treat as DEFECT").
"""

from __future__ import annotations

from dataclasses import dataclass

from msfc.core.errors import VisionError
from msfc.domain import InspectionResult, ModelInfo, RawVerdict
from msfc.vision.frame import Frame
from msfc.vision.inference import InferenceOutput


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Decision boundary on ``class_scores["DEFECT"]`` (FR-VIS-05, VT-03).

    ``defect_at ± uncertain_band`` is the UNCERTAIN zone; outside it the verdict is GOOD or
    DEFECT. Values are chosen by :func:`~msfc.vision.evaluation.evaluate` sweeping a range
    and picking a documented operating point — never guessed.
    """

    defect_at: float = 0.5
    uncertain_band: float = 0.05

    def __post_init__(self) -> None:
        if not (0.0 <= self.defect_at <= 1.0):
            raise VisionError(f"defect_at must be in [0, 1], got {self.defect_at!r}")
        if self.uncertain_band < 0.0:
            raise VisionError(f"uncertain_band must be >= 0, got {self.uncertain_band!r}")


def postprocess(
    output: InferenceOutput,
    thresholds: Thresholds,
    *,
    product_id: str,
    model: ModelInfo,
    frame: Frame | None = None,
) -> InspectionResult:
    """Turn one :class:`InferenceOutput` into an :class:`InspectionResult` for *product_id*."""
    defect_score = output.class_scores["DEFECT"]
    lower = thresholds.defect_at - thresholds.uncertain_band
    upper = thresholds.defect_at + thresholds.uncertain_band

    if defect_score >= upper:
        verdict, confidence = RawVerdict.DEFECT, defect_score
    elif defect_score <= lower:
        verdict, confidence = RawVerdict.GOOD, 1.0 - defect_score
    else:
        verdict, confidence = RawVerdict.UNCERTAIN, 0.5

    timings = dict(output.timings_ms)
    timings.setdefault("total", sum(output.timings_ms.values()))

    return InspectionResult(
        product_id=product_id,
        verdict=verdict,
        confidence=min(max(confidence, 0.0), 1.0),
        model=model,
        timings_ms=timings,
        class_scores=dict(output.class_scores),
        frame_seq=frame.seq if frame is not None else None,
    )
