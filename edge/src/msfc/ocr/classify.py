"""Result classification (P3.8) and wrapping into the shared decision-layer type (P3.9).

Rules, exactly as specified by the PO and no more:
  - OK + confidence >= threshold                      -> GOOD
  - EXPIRED / FORMAT_INVALID / LABEL_MISSING /
    LABEL_MISALIGNED, confidence >= threshold,
    and NOT ambiguous                                  -> DEFECT
  - UNREADABLE                                          -> UNCERTAIN (always -- can't classify
                                                           what couldn't be read at all)
  - ambiguous == True                                   -> UNCERTAIN (never DEFECT: P3.8 "do
                                                           not force uncertain OCR into GOOD/DEFECT")
  - confidence < threshold                               -> UNCERTAIN, regardless of reason

``to_inspection_result`` produces the exact same ``msfc.domain.InspectionResult`` type
``msfc.vision.postprocess.postprocess()`` produces, so it plugs into
``msfc.decision.DecisionEngine.decide()`` — which already accepts *any number* of inspection
channels and combines them with "any DEFECT wins" (msfc/decision/engine.py) — with zero changes
to msfc.decision (P3.9: "without unnecessarily rewriting P1").
"""

from __future__ import annotations

from msfc.domain import InspectionResult, ModelInfo, RawVerdict
from msfc.ocr.models import OcrReasonCode, OcrValidationResult

_DEFECT_REASONS = frozenset({
    OcrReasonCode.EXPIRED, OcrReasonCode.FORMAT_INVALID,
    OcrReasonCode.LABEL_MISSING, OcrReasonCode.LABEL_MISALIGNED,
})


def classify(result: OcrValidationResult, *, min_confidence: float) -> RawVerdict:
    if result.reason is OcrReasonCode.UNREADABLE:
        return RawVerdict.UNCERTAIN
    if result.ambiguous:
        return RawVerdict.UNCERTAIN
    if result.confidence < min_confidence:
        return RawVerdict.UNCERTAIN
    if result.reason is OcrReasonCode.OK:
        return RawVerdict.GOOD
    if result.reason in _DEFECT_REASONS:
        return RawVerdict.DEFECT
    return RawVerdict.UNCERTAIN  # unreachable while OcrReasonCode has only the 6 FR-OCR-04 values


def to_inspection_result(
    result: OcrValidationResult,
    verdict: RawVerdict,
    *,
    product_id: str,
    model: ModelInfo,
    timings_ms: dict[str, float],
    frame_seq: int | None = None,
) -> InspectionResult:
    """Wrap a classified OCR result into the same domain type vision inspections use."""
    timings = dict(timings_ms)
    timings.setdefault("total", sum(timings_ms.values()))
    return InspectionResult(
        product_id=product_id,
        verdict=verdict,
        confidence=result.confidence,
        model=model,
        timings_ms=timings,
        class_scores={},  # OCR's signal is discrete (reason code), not a continuous class score
        frame_seq=frame_seq,
    )
