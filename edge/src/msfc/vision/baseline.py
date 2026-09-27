"""Classical-CV baseline inference engine (ADR-0010, P1.3 "AI Baseline").

Approach: calibrate a mean "GOOD" template from a handful of reference images, then score
any new image by its mean absolute grayscale difference from that template. This is the
simplest classifier that can meaningfully separate the three synthetic defect types in
docs/DATASET_SPEC.md (a big dark MARK, a missing STICKER, and a subtle SCRATCH) while being
completely dependency-free (no training, no GPU) — exactly what ADR-0010 asks the baseline
to be before the CNN pipeline exists.
"""

from __future__ import annotations

import math
import time
from typing import Sequence

import cv2
import numpy as np

from msfc.core.errors import VisionError
from msfc.vision.inference import InferenceOutput


class ClassicCvBaseline:
    """Distance-from-reference-template classifier. See module docstring for the approach."""

    name = "classic_cv_baseline"
    version = "0.1.0"

    def __init__(self, *, reference_images: Sequence[np.ndarray], defect_threshold: float,
                 sensitivity: float = 0.5) -> None:
        """
        Args:
            reference_images: one or more known-GOOD, already-preprocessed images (same
                shape as what :meth:`predict` will receive) used to build the template.
            defect_threshold: mean-abs-difference value above which an image is scored as
                more likely DEFECT than GOOD (calibrate this against real reference data;
                see docs/DATASET_SPEC.md — never hard-code a number derived from synthetic
                data as if it applied to real products).
            sensitivity: controls how sharply the score transitions around the threshold
                (smaller = sharper). Must be > 0.
        """
        if not reference_images:
            raise VisionError("ClassicCvBaseline requires at least one reference image")
        if defect_threshold <= 0:
            raise VisionError(f"defect_threshold must be > 0, got {defect_threshold!r}")
        if sensitivity <= 0:
            raise VisionError(f"sensitivity must be > 0, got {sensitivity!r}")

        grays = [self._to_gray(img) for img in reference_images]
        shapes = {g.shape for g in grays}
        if len(shapes) > 1:
            raise VisionError(f"reference images must all share one shape, got {shapes}")

        self._reference = np.mean(grays, axis=0)
        self._threshold = defect_threshold
        self._sensitivity = sensitivity

    @staticmethod
    def _to_gray(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        return image.astype(np.float32)

    def predict(self, image: np.ndarray) -> InferenceOutput:
        start = time.perf_counter()
        gray = self._to_gray(image)
        if gray.shape != self._reference.shape:
            raise VisionError(
                f"image shape {gray.shape} does not match the calibrated reference {self._reference.shape}"
            )
        score = float(np.abs(gray - self._reference).mean())
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        # Logistic mapping centred on the threshold: score==threshold -> 0.5, and the curve
        # widens/narrows with `sensitivity` (a fraction of the threshold, not an absolute
        # pixel value, so the same default works across different image sizes/contrasts).
        margin = score - self._threshold
        scale = max(self._threshold * self._sensitivity, 1e-6)
        defect_prob = 1.0 / (1.0 + math.exp(-margin / scale))

        return InferenceOutput(
            class_scores={"GOOD": 1.0 - defect_prob, "DEFECT": defect_prob},
            timings_ms={"inference": elapsed_ms},
        )
