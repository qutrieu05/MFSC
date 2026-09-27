"""The InferenceEngine interface (IF-04) every backend implements: classical CV baseline
today (P1.3), an ONNX-exported CNN also today (as a synthetic smoke test — see
msfc/vision/training.py), and later a model trained on real data (P1.11) — all interchangeable
without touching msfc.decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from msfc.core.errors import VisionError


@dataclass(frozen=True, slots=True)
class InferenceOutput:
    """Raw scores from one backend, before :func:`~msfc.vision.postprocess.postprocess`
    turns them into a domain :class:`~msfc.domain.InspectionResult`."""

    class_scores: dict[str, float]
    timings_ms: dict[str, float]

    def __post_init__(self) -> None:
        if "DEFECT" not in self.class_scores:
            raise VisionError("class_scores must include a 'DEFECT' key")


class InferenceEngine(Protocol):
    """A backend that scores one preprocessed image (already cropped+resized)."""

    name: str
    version: str

    def predict(self, image: np.ndarray) -> InferenceOutput: ...
