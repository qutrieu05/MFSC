"""Image preprocessing for label/expiry text (P3.3).

Deliberately does NOT import msfc.vision — ARCHITECTURE.md section 7.2 and
edge/tests/unit/test_layer_dependencies.py already declare ``ocr`` a sibling of ``vision``,
both depending only on ``core``+``domain``. A near-identical ``RoiConfig``/``crop`` exists in
msfc.vision.preprocess for camera frames; this module's own, smaller copy is intentional, not
an oversight — see D-041, DECISIONS.md.

Each step is a small, independent, directly testable function (P3.3: "keep preprocessing
modular"); ``preprocess()`` only composes the ones a caller opts into via ``PreprocessConfig``.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from msfc.core.errors import OcrError


@dataclass(frozen=True, slots=True)
class RoiConfig:
    """A crop region, in source-image pixel coordinates."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise OcrError(f"RoiConfig width/height must be > 0, got {self.width}x{self.height}")
        if self.x < 0 or self.y < 0:
            raise OcrError(f"RoiConfig x/y must be >= 0, got ({self.x}, {self.y})")


@dataclass(frozen=True, slots=True)
class PreprocessConfig:
    """Which steps ``preprocess()`` runs, and with what parameters. Every step is optional —
    an empty/default config only resizes (P3.3: don't force steps a caller doesn't need)."""

    roi: RoiConfig | None = None
    target_size: tuple[int, int] | None = (320, 120)  # (width, height); None = no resize
    grayscale: bool = True
    contrast_alpha: float = 1.0  # 1.0 = no change; cv2.convertScaleAbs gain
    contrast_beta: float = 0.0  # brightness offset
    denoise: bool = False
    threshold: bool = False  # adaptive binarization, applied after grayscale+denoise
    max_deskew_deg: float = 0.0  # 0 = disabled; otherwise auto-correct up to this many degrees


def crop_roi(image: np.ndarray, roi: RoiConfig) -> np.ndarray:
    height, width = image.shape[:2]
    if roi.x + roi.width > width or roi.y + roi.height > height:
        raise OcrError(
            f"RoiConfig {roi} exceeds image bounds {width}x{height}"
        )
    return image[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]


def resize(image: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
    width, height = target_size
    if width <= 0 or height <= 0:
        raise OcrError(f"target_size must be positive, got {target_size!r}")
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def adjust_contrast(image: np.ndarray, *, alpha: float = 1.5, beta: float = 0.0) -> np.ndarray:
    if alpha <= 0:
        raise OcrError(f"contrast alpha must be > 0, got {alpha!r}")
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)


def denoise(image: np.ndarray) -> np.ndarray:
    """Median blur: cheap and effective against the salt-and-pepper-style sensor noise
    ``msfc.ocr.synthetic`` injects for the "OCR noise" fixture — not a general-purpose
    denoiser, deliberately kept simple (P3.3: don't over-engineer without tests)."""
    return cv2.medianBlur(image, 3)


def adaptive_threshold(image: np.ndarray) -> np.ndarray:
    gray = image if image.ndim == 2 else to_grayscale(image)
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, blockSize=11, C=2
    )


def estimate_skew_deg(image: np.ndarray) -> float:
    """Estimate the rotation (degrees) of the dominant text/content region, via the minimum-
    area bounding rectangle of non-background pixels. Returns 0.0 for an empty/blank image
    (nothing to deskew) rather than raising — a blank label is a content problem for
    validation to report (LABEL_MISSING), not a preprocessing failure."""
    gray = image if image.ndim == 2 else to_grayscale(image)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is None or len(coords) < 3:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    # cv2.minAreaRect returns an angle in (-90, 0]; normalize to the smallest rotation
    # (in degrees) that would make the rectangle's edges axis-aligned.
    if angle < -45:
        angle = 90 + angle
    return float(angle)


def deskew(image: np.ndarray, angle_deg: float) -> np.ndarray:
    if angle_deg == 0.0:
        return image
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)


def preprocess(image: np.ndarray, config: PreprocessConfig) -> np.ndarray:
    """Run the steps *config* enables, in a fixed, documented order: crop -> resize ->
    grayscale -> denoise -> contrast -> deskew -> threshold."""
    out = image
    if config.roi is not None:
        out = crop_roi(out, config.roi)
    if config.target_size is not None:
        out = resize(out, config.target_size)
    if config.grayscale:
        out = to_grayscale(out)
    if config.denoise:
        out = denoise(out)
    if config.contrast_alpha != 1.0 or config.contrast_beta != 0.0:
        out = adjust_contrast(out, alpha=config.contrast_alpha, beta=config.contrast_beta)
    if config.max_deskew_deg > 0:
        angle = estimate_skew_deg(out)
        if abs(angle) <= config.max_deskew_deg:
            out = deskew(out, angle)
    if config.threshold:
        out = adaptive_threshold(out)
    return out
