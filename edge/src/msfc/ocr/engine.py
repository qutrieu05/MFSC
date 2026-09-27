"""OCR engine abstraction (P3.2) — mirrors msfc.vision.inference.InferenceEngine's shape.

``Mock OCR -> same interface -> Real OCR later``: any future real backend (Tesseract,
PaddleOCR, a cloud API) only needs to implement ``OcrEngine``; nothing upstream or downstream
(preprocess/normalize/extract/validate/classify/pipeline) hard-codes a specific library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from msfc.ocr.models import OcrOutput


class OcrEngine(Protocol):
    """A backend that reads text from one preprocessed image."""

    name: str
    version: str

    def read(self, image: np.ndarray) -> OcrOutput: ...


@dataclass(frozen=True, slots=True)
class MockOcrEngine:
    """Returns a single, fixed :class:`OcrOutput` regardless of the input image.

    For unit tests of the stages *downstream* of OCR (normalize/extract/validate/classify)
    that need a known, constant OCR result and don't care what image they're "reading."
    """

    name: str = "mock-ocr"
    version: str = "1"
    fixed_output: OcrOutput = OcrOutput(raw_text="", confidence=0.0)

    def read(self, image: np.ndarray) -> OcrOutput:
        if image.ndim not in (2, 3):
            raise ValueError(f"expected a 2D or 3D image array, got shape {image.shape}")
        return self.fixed_output


class FixtureOcrEngine:
    """Deterministic "test OCR" driven by explicit ``set_next_output()`` calls — the same
    pattern ``tests/integration/test_full_pipeline_mvp.py``'s ``_OracleVisionEngine`` already
    uses for vision, reused here rather than reinvented (P3.2 rule 2).

    Deliberately does NOT try to identify *which* fixture ``read()``'s image argument
    corresponds to (e.g. by object identity): ``msfc.ocr.pipeline.run_ocr_pipeline`` calls
    ``preprocess()`` before ``engine.read()``, which always returns a *new* array — pixel- or
    identity-based lookup would silently break the moment preprocessing changes. The caller
    (a fixture loop, a test) sets the expected output immediately before driving the pipeline,
    exactly like the vision oracle's ``set_next_label()``.
    """

    name = "fixture-ocr"
    version = "1"

    def __init__(self) -> None:
        self._next_output: OcrOutput | None = None

    def set_next_output(self, output: OcrOutput) -> None:
        self._next_output = output

    def read(self, image: np.ndarray) -> OcrOutput:
        if image.ndim not in (2, 3):
            raise ValueError(f"expected a 2D or 3D image array, got shape {image.shape}")
        if self._next_output is None:
            raise RuntimeError("FixtureOcrEngine.read() called before set_next_output()")
        return self._next_output
