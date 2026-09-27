"""Camera / Computer Vision / Edge AI (Layer 3, IF-03..05).

Depends only on ``msfc.core`` and ``msfc.domain`` (ARCHITECTURE.md section 7.2) — this
package has no idea MQTT or the Decision Engine's business rules exist; it turns frames into
:class:`~msfc.domain.InspectionResult` objects and nothing else.
"""

from __future__ import annotations

from msfc.vision.baseline import ClassicCvBaseline
from msfc.vision.frame import Frame, FrameSource
from msfc.vision.inference import InferenceEngine, InferenceOutput
from msfc.vision.postprocess import Thresholds, postprocess
from msfc.vision.preprocess import RoiConfig, crop_roi, preprocess, resize
from msfc.vision.evaluation import EvalReport, evaluate
from msfc.vision.sources import (
    ImageFolderFrameSource,
    SyntheticFrameSource,
    UsbCameraFrameSource,
    VideoFileFrameSource,
)
from msfc.vision.synthetic import DEFECT_SUB_LABELS, LabeledSample, generate_dataset, generate_sample

__all__ = [
    "Frame",
    "FrameSource",
    "SyntheticFrameSource",
    "ImageFolderFrameSource",
    "VideoFileFrameSource",
    "UsbCameraFrameSource",
    "RoiConfig",
    "crop_roi",
    "resize",
    "preprocess",
    "InferenceEngine",
    "InferenceOutput",
    "ClassicCvBaseline",
    "Thresholds",
    "postprocess",
    "EvalReport",
    "evaluate",
    "LabeledSample",
    "DEFECT_SUB_LABELS",
    "generate_sample",
    "generate_dataset",
]
