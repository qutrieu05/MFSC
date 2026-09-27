"""P3.2: OCR engine abstraction — mock + deterministic fixture engine."""

from __future__ import annotations

import numpy as np
import pytest

from msfc.ocr.engine import FixtureOcrEngine, MockOcrEngine
from msfc.ocr.models import OcrOutput


def test_mock_engine_returns_fixed_output_regardless_of_image() -> None:
    engine = MockOcrEngine(fixed_output=OcrOutput(raw_text="PROD-A EXP 01/06/2027", confidence=0.9))
    out1 = engine.read(np.zeros((10, 10, 3), dtype=np.uint8))
    out2 = engine.read(np.ones((20, 30), dtype=np.uint8) * 255)
    assert out1 == out2 == OcrOutput(raw_text="PROD-A EXP 01/06/2027", confidence=0.9)


def test_mock_engine_rejects_bad_image_shape() -> None:
    engine = MockOcrEngine()
    with pytest.raises(ValueError, match="2D or 3D"):
        engine.read(np.zeros((2, 2, 2, 2)))


def test_mock_engine_satisfies_the_ocr_engine_protocol_attributes() -> None:
    engine = MockOcrEngine()
    assert isinstance(engine.name, str) and engine.name
    assert isinstance(engine.version, str) and engine.version


def test_fixture_engine_returns_the_last_armed_output() -> None:
    engine = FixtureOcrEngine()
    engine.set_next_output(OcrOutput(raw_text="A", confidence=0.5))
    assert engine.read(np.zeros((5, 5))).raw_text == "A"

    engine.set_next_output(OcrOutput(raw_text="B", confidence=0.9))
    assert engine.read(np.zeros((5, 5))).raw_text == "B"


def test_fixture_engine_raises_if_read_before_armed() -> None:
    engine = FixtureOcrEngine()
    with pytest.raises(RuntimeError, match="set_next_output"):
        engine.read(np.zeros((5, 5)))


def test_fixture_engine_is_unaffected_by_preprocessing_changing_the_array_identity() -> None:
    """The bug this regression-guards: an id()-keyed lookup would break the moment
    preprocess() returns a new array (resize/grayscale/etc. always do)."""
    engine = FixtureOcrEngine()
    original = np.zeros((10, 10, 3), dtype=np.uint8)
    engine.set_next_output(OcrOutput(raw_text="X", confidence=0.8))

    transformed = original.copy()  # simulates what preprocess() would hand to read()
    assert transformed is not original
    assert engine.read(transformed).raw_text == "X"
