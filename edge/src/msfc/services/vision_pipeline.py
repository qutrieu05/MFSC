"""P6.2: the vision-channel composition step, following the exact
``Frame -> preprocess -> InferenceEngine.predict -> postprocess -> InspectionResult`` sequence
``tests/integration/test_full_pipeline_mvp.py``'s ``_Pipeline._Pipeline.run_one_product`` has
already proven correct by hand for every P1 test in that file.

Deliberately lives in ``msfc.services``, not ``msfc.vision`` -- the PO's Phase 6 directive says
"do NOT rewrite the existing Vision/OCR/Decision logic. Compose existing modules"; unlike
``msfc.ocr`` (which already has its own ``pipeline.py`` composing ITS OWN steps, P3.9),
``msfc.vision`` has no such composition function yet, and adding one to ``msfc.vision`` itself
would be an (unrequested) change to a package the PO said not to touch. This module only calls
``msfc.vision``'s existing public interface (``FrameSource``/``preprocess``/``InferenceEngine``/
``postprocess``) -- nothing here duplicates vision logic.

Unlike ``msfc.ocr.pipeline.run_ocr_pipeline`` (which never raises for a *content* problem and
always resolves to a classified result), vision has no such "unreadable but still a legitimate
answer" concept -- a missing frame or a failed inference is a genuine absence of a vision
channel for this cycle, not an UNCERTAIN verdict. This function therefore raises (VisionError,
or whatever the engine itself raises) rather than inventing a fake result; the caller
(``msfc.services.pipeline.run_product_cycle``) is where "treat a vision failure as one missing
channel, never as a fabricated GOOD" is decided (P6.10: "AI failure must NOT become continue
blindly").
"""

from __future__ import annotations

from msfc.domain import InspectionResult, ModelInfo
from msfc.vision import Frame, InferenceEngine, RoiConfig, Thresholds, postprocess, preprocess


def run_vision_pipeline(
    frame: Frame,
    *,
    engine: InferenceEngine,
    roi: RoiConfig,
    thresholds: Thresholds,
    model: ModelInfo,
    product_id: str,
) -> InspectionResult:
    """Run one frame through the vision channel. Raises on any failure (bad ROI, engine
    error) -- see module docstring for why this is intentional, not an oversight."""
    processed = preprocess(frame, roi)
    output = engine.predict(processed)
    return postprocess(output, thresholds, product_id=product_id, model=model, frame=frame)


__all__ = ["run_vision_pipeline"]
