"""Preprocessing: crop the region of interest, resize to the model's input size.

Kept deliberately tiny and dependency-free beyond OpenCV — FR-VIS-03 calls this "a pipeline
of configurable steps"; today that pipeline is exactly two steps (crop, resize). Add a step
here (and a config field in ``[vision]``, once that section exists) rather than growing this
into a framework nobody asked for yet.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from msfc.core.errors import VisionError
from msfc.vision.frame import Frame


@dataclass(frozen=True, slots=True)
class RoiConfig:
    """Region of interest, in the source image's pixel coordinates, plus the model's
    expected input size (docs/HARDWARE_INTERFACE.md section 3: "ROI sản phẩm ≥ 200x200 px"
    is a real-camera target; synthetic frames are 128x128, so tests use a smaller ROI)."""

    x: int
    y: int
    width: int
    height: int
    target_size: tuple[int, int] = (128, 128)

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise VisionError(f"ROI origin must be >= 0, got ({self.x}, {self.y})")
        if self.width <= 0 or self.height <= 0:
            raise VisionError(f"ROI width/height must be > 0, got ({self.width}, {self.height})")
        tw, th = self.target_size
        if tw <= 0 or th <= 0:
            raise VisionError(f"target_size must be > 0, got {self.target_size!r}")


def crop_roi(image: np.ndarray, roi: RoiConfig) -> np.ndarray:
    """Crop *image* to *roi*, raising if the ROI does not fit inside the image."""
    height, width = image.shape[:2]
    x2, y2 = roi.x + roi.width, roi.y + roi.height
    if x2 > width or y2 > height:
        raise VisionError(
            f"ROI {(roi.x, roi.y, roi.width, roi.height)} does not fit inside image of size {(width, height)}"
        )
    return image[roi.y:y2, roi.x:x2]


def resize(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Resize to *size* = (width, height) using area interpolation (good for shrinking)."""
    return cv2.resize(image, size, interpolation=cv2.INTER_AREA)


def preprocess(frame: Frame, roi: RoiConfig) -> np.ndarray:
    """Crop then resize one frame to the model's expected input size (FR-VIS-03)."""
    return resize(crop_roi(frame.image, roi), roi.target_size)
