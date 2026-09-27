"""OCR / expiry-date / label verification (Layer 3, Phase 3 — FR-OCR).

Depends only on ``msfc.core`` and ``msfc.domain`` (ARCHITECTURE.md section 7.2, sibling of
``msfc.vision``) — this package has no idea MQTT or the Decision Engine's business rules exist;
it turns label images into :class:`~msfc.domain.InspectionResult` objects and nothing else,
exactly like ``msfc.vision`` does for the camera channel.
"""

from __future__ import annotations

from msfc.ocr.classify import classify, to_inspection_result
from msfc.ocr.engine import FixtureOcrEngine, MockOcrEngine, OcrEngine
from msfc.ocr.models import (
    BoundingBox,
    DateCandidate,
    DateExtractionResult,
    DetectedField,
    OcrOutput,
    OcrReasonCode,
    OcrValidationResult,
)
from msfc.ocr.pipeline import run_ocr_pipeline
from msfc.ocr.preprocess import PreprocessConfig, RoiConfig, preprocess
from msfc.ocr.synthetic import LabeledLabelSample, drive_fixture_engine, generate_fixtures
from msfc.ocr.text import SUPPORTED_DATE_FORMATS, extract_dates, normalize_text
from msfc.ocr.validate import LabelValidationConfig, validate_label

__all__ = [
    "BoundingBox",
    "OcrOutput",
    "OcrReasonCode",
    "DetectedField",
    "DateCandidate",
    "DateExtractionResult",
    "OcrValidationResult",
    "OcrEngine",
    "MockOcrEngine",
    "FixtureOcrEngine",
    "RoiConfig",
    "PreprocessConfig",
    "preprocess",
    "SUPPORTED_DATE_FORMATS",
    "normalize_text",
    "extract_dates",
    "LabelValidationConfig",
    "validate_label",
    "classify",
    "to_inspection_result",
    "run_ocr_pipeline",
    "LabeledLabelSample",
    "generate_fixtures",
    "drive_fixture_engine",
]
