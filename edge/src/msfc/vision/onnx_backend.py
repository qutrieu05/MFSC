"""ONNX Runtime inference backend (P1.3 deferred sub-item — decisions D-033/D-035).

Implements the same :class:`~msfc.vision.InferenceEngine` interface
:class:`~msfc.vision.ClassicCvBaseline` does, so it drops straight into the existing
:func:`~msfc.vision.postprocess.postprocess` -> :class:`~msfc.decision.DecisionEngine`
pipeline with no changes on either side — that interchangeability is the whole point of
ADR-0010's layering.

Not imported by ``msfc.vision``'s package ``__init__`` on purpose: it requires
``onnxruntime``, which ``ClassicCvBaseline`` does not need. Import directly:
``from msfc.vision.onnx_backend import OnnxInferenceEngine``.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import onnxruntime as ort

from msfc.core.errors import VisionError
from msfc.vision.inference import InferenceOutput

_INDEX_TO_LABEL = ("GOOD", "DEFECT")  # must match msfc.vision.training._LABEL_TO_INDEX


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


class OnnxInferenceEngine:
    """Loads a ``.onnx`` model (from :func:`msfc.vision.training.export_onnx`) and serves
    predictions through :class:`~msfc.vision.InferenceEngine`.

    The model's own name/version are not recoverable from the ONNX file alone, so both are
    passed in explicitly at construction and should identify *this specific export* (e.g.
    include the training run's date or checkpoint hash) — never a bare "cnn" that could be
    confused with a different training run later.
    """

    def __init__(self, onnx_path: Path, *, name: str, version: str) -> None:
        if not onnx_path.exists():
            raise VisionError(f"ONNX model not found: {onnx_path}")
        self.name = name
        self.version = version
        self._session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        inputs = self._session.get_inputs()
        if len(inputs) != 1:
            raise VisionError(f"expected exactly one ONNX input, got {len(inputs)}: {[i.name for i in inputs]}")
        self._input_name = inputs[0].name
        self._input_shape = inputs[0].shape  # e.g. [1, 3, 64, 64] (batch may be symbolic)

    def predict(self, image: np.ndarray) -> InferenceOutput:
        """*image* must already be preprocessed (HxWx3 uint8, BGR — the same shape
        :func:`msfc.vision.preprocess.preprocess` produces for every other engine)."""
        if image.ndim != 3 or image.shape[2] != 3:
            raise VisionError(f"expected an HxWx3 image, got shape {image.shape}")
        start = time.perf_counter()
        chw = (image.astype(np.float32) / 255.0).transpose(2, 0, 1)[None, ...]  # -> 1x3xHxW
        logits = self._session.run(None, {self._input_name: chw})[0][0]
        probs = _softmax(logits)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return InferenceOutput(
            class_scores={"GOOD": float(probs[0]), "DEFECT": float(probs[1])},
            timings_ms={"inference": elapsed_ms},
        )
