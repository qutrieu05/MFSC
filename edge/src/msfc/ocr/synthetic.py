"""P3.10 deterministic synthetic fixtures — the 12 scenarios named in the PO's directive.

Mirrors ``msfc.vision.synthetic``'s discipline (D-026): every image here is generated
locally, 0 VND, no internet/real OCR service, and no accuracy claim is made about real
products. Images are rendered with the intended text drawn on them (via ``cv2.putText``) so
preprocessing has real pixels to operate on and a fixture is visually inspectable — but the
:class:`~msfc.ocr.engine.FixtureOcrEngine` these samples are registered with reads the *ground
truth* text/confidence attached to each sample, not the rendered pixels (D-043, DECISIONS.md):
this proves the P3.9 pipeline wiring, not a real OCR algorithm's accuracy on rendered text.

LABEL_MISALIGNED is NOT one of the 12 named fixtures (the PO's list doesn't include a skew
scenario) — it's covered separately by direct unit tests of ``msfc.ocr.validate.validate_label``
with an explicit ``skew_deg`` argument (test_ocr_validate.py), not by a synthetic image here.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from msfc.domain import RawVerdict
from msfc.ocr.engine import FixtureOcrEngine
from msfc.ocr.models import OcrOutput

IMAGE_SIZE = (320, 120)  # (width, height) — matches PreprocessConfig's default target_size


def _render_label_image(text: str) -> np.ndarray:
    width, height = IMAGE_SIZE
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.putText(image, text[:40], (8, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
                cv2.LINE_AA)
    return image


@dataclass(frozen=True, slots=True)
class LabeledLabelSample:
    """One synthetic fixture: a rendered image plus the ground truth an OCR engine "reads"
    (used to drive :class:`~msfc.ocr.engine.FixtureOcrEngine`) and the verdict a correct
    pipeline run is expected to produce, for the test to assert against."""

    image: np.ndarray
    scenario: str
    raw_text: str
    ocr_confidence: float
    session_id: str
    expected_verdict: RawVerdict


def _sample(scenario: str, raw_text: str, confidence: float, *, session_id: str,
            expected_verdict: RawVerdict) -> LabeledLabelSample:
    return LabeledLabelSample(
        image=_render_label_image(raw_text), scenario=scenario, raw_text=raw_text,
        ocr_confidence=confidence, session_id=session_id, expected_verdict=expected_verdict,
    )


def generate_fixtures(session_id: str = "s01") -> tuple[LabeledLabelSample, ...]:
    """The 12 scenarios named in the PO's Phase 3 directive, in order."""
    return (
        _sample("valid_expiry_date", "PROD-A EXP 01/06/2027", 0.92,
                session_id=session_id, expected_verdict=RawVerdict.GOOD),
        _sample("expired_product", "PROD-A EXP 01/06/2020", 0.92,
                session_id=session_id, expected_verdict=RawVerdict.DEFECT),
        _sample("impossible_date", "PROD-A EXP 31/02/2027", 0.92,
                session_id=session_id, expected_verdict=RawVerdict.DEFECT),
        _sample("missing_expiry", "PROD-A NO DATE PRESENT", 0.92,
                session_id=session_id, expected_verdict=RawVerdict.DEFECT),
        _sample("wrong_product_identifier", "PROD-Z EXP 01/06/2027", 0.92,
                session_id=session_id, expected_verdict=RawVerdict.DEFECT),
        _sample("valid_product_and_expiry", "PROD-A BATCH123 EXP 15/12/2028", 0.95,
                session_id=session_id, expected_verdict=RawVerdict.GOOD),
        _sample("low_ocr_confidence", "PROD-A EXP 01/06/2027", 0.30,
                session_id=session_id, expected_verdict=RawVerdict.UNCERTAIN),
        _sample("ambiguous_ocr", "PROD-A EXP 01/06/2027 OR 02/07/2027", 0.92,
                session_id=session_id, expected_verdict=RawVerdict.UNCERTAIN),
        _sample("multiple_date_formats", "PROD-A EXP 2027-06-01", 0.92,  # YYYY-MM-DD, not the default format
                session_id=session_id, expected_verdict=RawVerdict.GOOD),
        _sample("ocr_noise", "PROD-A EXP O1/O6/2O27", 0.75,  # 'O' for '0' -- date-scoped confusion, product token clean
                session_id=session_id, expected_verdict=RawVerdict.GOOD),
        _sample("empty_ocr_result", "", 0.0,
                session_id=session_id, expected_verdict=RawVerdict.UNCERTAIN),
        _sample("malformed_ocr_result", "@#$%^&*()", 0.70,  # confidence kept >= threshold on
                # purpose, so this isolates "text read but nonsensical" from "low confidence"
                # (already covered by low_ocr_confidence above), per P3.10's 12 distinct scenarios
                session_id=session_id, expected_verdict=RawVerdict.DEFECT),
    )


def drive_fixture_engine(engine: FixtureOcrEngine, sample: LabeledLabelSample) -> None:
    """Arm *engine* with *sample*'s ground truth — call this immediately before running the
    pipeline on ``sample.image`` (mirrors ``_OracleVisionEngine.set_next_label()``)."""
    engine.set_next_output(OcrOutput(raw_text=sample.raw_text, confidence=sample.ocr_confidence))
