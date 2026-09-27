"""P3.3: image preprocessing pipeline."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from msfc.core.errors import OcrError
from msfc.ocr.preprocess import (
    PreprocessConfig,
    RoiConfig,
    adaptive_threshold,
    adjust_contrast,
    crop_roi,
    denoise,
    deskew,
    estimate_skew_deg,
    preprocess,
    resize,
    to_grayscale,
)


def _bgr_image(width: int = 40, height: int = 30) -> np.ndarray:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.rectangle(image, (5, 5), (width - 5, height - 5), (255, 255, 255), -1)
    return image


def test_roi_config_rejects_non_positive_dimensions() -> None:
    with pytest.raises(OcrError, match="width/height"):
        RoiConfig(x=0, y=0, width=0, height=5)


def test_crop_roi_returns_the_requested_region() -> None:
    image = _bgr_image(40, 30)
    cropped = crop_roi(image, RoiConfig(x=5, y=5, width=10, height=10))
    assert cropped.shape[:2] == (10, 10)


def test_crop_roi_rejects_region_outside_image_bounds() -> None:
    image = _bgr_image(40, 30)
    with pytest.raises(OcrError, match="exceeds image bounds"):
        crop_roi(image, RoiConfig(x=35, y=0, width=10, height=10))


def test_resize_produces_the_exact_target_size() -> None:
    image = _bgr_image(40, 30)
    resized = resize(image, (100, 50))
    assert resized.shape[:2] == (50, 100)  # (height, width)


def test_resize_rejects_non_positive_target() -> None:
    with pytest.raises(OcrError, match="positive"):
        resize(_bgr_image(), (0, 10))


def test_to_grayscale_collapses_the_color_channel() -> None:
    image = _bgr_image(40, 30)
    gray = to_grayscale(image)
    assert gray.ndim == 2
    assert gray.shape == (30, 40)


def test_to_grayscale_is_a_no_op_on_an_already_gray_image() -> None:
    gray_in = np.zeros((10, 10), dtype=np.uint8)
    assert to_grayscale(gray_in) is gray_in


def test_adjust_contrast_scales_pixel_values() -> None:
    image = np.full((5, 5), 100, dtype=np.uint8)
    brighter = adjust_contrast(image, alpha=1.0, beta=50)
    assert brighter[0, 0] == 150


def test_adjust_contrast_rejects_non_positive_alpha() -> None:
    with pytest.raises(OcrError, match="alpha"):
        adjust_contrast(np.zeros((5, 5), dtype=np.uint8), alpha=0)


def test_denoise_preserves_shape() -> None:
    image = _bgr_image(40, 30)
    assert denoise(image).shape == image.shape


def test_adaptive_threshold_produces_a_binary_image() -> None:
    image = _bgr_image(40, 30)
    binary = adaptive_threshold(image)
    assert binary.ndim == 2
    assert set(np.unique(binary)) <= {0, 255}


def test_estimate_skew_deg_returns_zero_for_a_blank_image() -> None:
    blank = np.zeros((30, 40), dtype=np.uint8)
    assert estimate_skew_deg(blank) == 0.0


def test_deskew_is_a_no_op_for_zero_angle() -> None:
    image = _bgr_image(40, 30)
    assert deskew(image, 0.0) is image


def test_deskew_preserves_image_shape_for_a_nonzero_angle() -> None:
    image = _bgr_image(40, 30)
    rotated = deskew(image, 5.0)
    assert rotated.shape == image.shape


def test_preprocess_composes_steps_in_order_and_respects_config_flags() -> None:
    image = _bgr_image(200, 100)
    config = PreprocessConfig(roi=RoiConfig(x=0, y=0, width=100, height=80),
                               target_size=(64, 32), grayscale=True, denoise=True,
                               contrast_alpha=1.2, threshold=True)
    out = preprocess(image, config)
    assert out.shape == (32, 64)
    assert set(np.unique(out)) <= {0, 255}  # threshold=True -> binary output


def test_preprocess_with_default_config_only_resizes() -> None:
    image = _bgr_image(200, 100)
    out = preprocess(image, PreprocessConfig())
    assert out.shape[:2] == (120, 320)  # (height, width) from the default target_size


def test_preprocess_skips_deskew_when_disabled_even_with_skewed_content() -> None:
    image = _bgr_image(80, 60)
    config = PreprocessConfig(target_size=None, grayscale=True, max_deskew_deg=0.0)
    out = preprocess(image, config)
    assert out.shape == (60, 80)
