"""Tests for msfc.vision.preprocess."""

from __future__ import annotations

import numpy as np
import pytest

from msfc.core.errors import VisionError
from msfc.vision import Frame, RoiConfig, crop_roi, preprocess, resize


def _frame(size: int = 128) -> Frame:
    image = np.arange(size * size * 3, dtype=np.uint8).reshape(size, size, 3)
    return Frame(image=image, seq=0, captured_mono_ms=0, source="test")


def test_crop_roi_extracts_the_requested_region() -> None:
    frame = _frame()
    roi = RoiConfig(x=10, y=20, width=30, height=40)
    cropped = crop_roi(frame.image, roi)
    assert cropped.shape == (40, 30, 3)
    assert np.array_equal(cropped, frame.image[20:60, 10:40])


def test_crop_roi_out_of_bounds_raises() -> None:
    frame = _frame(size=64)
    roi = RoiConfig(x=0, y=0, width=100, height=100)
    with pytest.raises(VisionError, match="does not fit"):
        crop_roi(frame.image, roi)


def test_resize_changes_dimensions() -> None:
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    resized = resize(image, (20, 10))
    assert resized.shape == (10, 20, 3)  # cv2.resize output is (height, width, channels)


def test_preprocess_crops_then_resizes() -> None:
    frame = _frame(size=128)
    roi = RoiConfig(x=0, y=0, width=64, height=64, target_size=(32, 16))
    result = preprocess(frame, roi)
    assert result.shape == (16, 32, 3)


@pytest.mark.parametrize("kwargs,match", [
    ({"x": -1, "y": 0, "width": 10, "height": 10}, "origin"),
    ({"x": 0, "y": -1, "width": 10, "height": 10}, "origin"),
    ({"x": 0, "y": 0, "width": 0, "height": 10}, "width/height"),
    ({"x": 0, "y": 0, "width": 10, "height": -5}, "width/height"),
    ({"x": 0, "y": 0, "width": 10, "height": 10, "target_size": (0, 5)}, "target_size"),
])
def test_roi_config_validates_its_fields(kwargs: dict, match: str) -> None:
    with pytest.raises(VisionError, match=match):
        RoiConfig(**kwargs)
