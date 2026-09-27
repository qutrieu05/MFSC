"""P3.9 end-to-end orchestration + P3.12 error handling.

    Image -> preprocess -> OCR engine -> normalize -> extract/validate -> classify
    -> InspectionResult -> (caller passes this to msfc.decision.DecisionEngine.decide()
       alongside any other channel's InspectionResult, unmodified)

This module does not import msfc.decision — per the layer rules, msfc.ocr stays a Layer-3
sibling of msfc.vision, and the caller (a future msfc.services, or a test/integration file
today) is the one that combines channels and calls DecisionEngine, exactly as
tests/integration/test_full_pipeline_mvp.py already does for vision.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

import numpy as np

from msfc.core.errors import OcrError
from msfc.domain import InspectionResult, ModelInfo, RawVerdict
from msfc.ocr.classify import classify, to_inspection_result
from msfc.ocr.engine import OcrEngine
from msfc.ocr.models import OcrReasonCode, OcrValidationResult
from msfc.ocr.preprocess import PreprocessConfig, estimate_skew_deg, preprocess
from msfc.ocr.text import normalize_text
from msfc.ocr.validate import LabelValidationConfig, validate_label


def run_ocr_pipeline(
    image: np.ndarray,
    *,
    engine: OcrEngine,
    preprocess_config: PreprocessConfig,
    label_config: LabelValidationConfig,
    reference_date: date,
    product_id: str,
    frame_seq: int | None = None,
) -> InspectionResult:
    """Run the full P3.9 flow. Never raises for a *content* problem (bad OCR, bad date,
    missing label) — those always resolve to a classified InspectionResult (P3.12:
    "failure behavior must be deterministic"). Only raises OcrError for a *pipeline*
    problem the caller must fix (bad image array, misconfigured preprocessing/label rules,
    an OCR engine that itself raises)."""
    timings: dict[str, float] = {}
    model = ModelInfo(name=engine.name, version=engine.version, backend="ocr")

    t0 = time.perf_counter()
    try:
        processed = preprocess(image, preprocess_config)
    except OcrError:
        raise  # a preprocessing failure is a caller bug (bad ROI/config), not OCR content -- re-raise
    timings["preprocess"] = (time.perf_counter() - t0) * 1000.0

    skew_deg = estimate_skew_deg(processed) if preprocess_config.max_deskew_deg > 0 else 0.0

    t0 = time.perf_counter()
    try:
        ocr_output = engine.read(processed)
    except Exception as exc:  # OCR engine unavailable/crashed (P3.12) -> deterministic UNREADABLE
        timings["ocr"] = (time.perf_counter() - t0) * 1000.0
        validation = OcrValidationResult(reason=OcrReasonCode.UNREADABLE, confidence=0.0,
                                          details={"cause": "ocr engine error", "error": str(exc)})
        verdict = classify(validation, min_confidence=label_config.min_confidence)
        return to_inspection_result(validation, verdict, product_id=product_id, model=model,
                                     timings_ms=timings, frame_seq=frame_seq)
    timings["ocr"] = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    normalized = normalize_text(ocr_output.raw_text)
    timings["normalize"] = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    validation = validate_label(normalized, ocr_output.confidence, config=label_config,
                                 reference_date=reference_date, skew_deg=skew_deg)
    timings["validate_and_extract"] = (time.perf_counter() - t0) * 1000.0

    verdict = classify(validation, min_confidence=label_config.min_confidence)
    return to_inspection_result(validation, verdict, product_id=product_id, model=model,
                                 timings_ms=timings, frame_seq=frame_seq)
