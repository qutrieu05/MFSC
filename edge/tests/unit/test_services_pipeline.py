"""P6.2/P6.5: per-product pipeline orchestration tests (pure, no bus)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import CellStateSnapshot, MachineState, ModelInfo
from msfc.ocr import FixtureOcrEngine, LabelValidationConfig, OcrOutput, PreprocessConfig
from msfc.services.pipeline import OcrStageConfig, VisionStageConfig, run_product_cycle
from msfc.services.platform_model import PipelineOutcome
from msfc.vision import Frame, InferenceOutput, RoiConfig, Thresholds

ROI = RoiConfig(x=0, y=0, width=16, height=16, target_size=(16, 16))
MODEL = ModelInfo(name="stub", version="1")
THRESHOLDS = Thresholds(defect_at=0.5, uncertain_band=0.05)
IDLE_STATE = CellStateSnapshot(machine_state=MachineState.IDLE)
RUNNING_STATE = CellStateSnapshot(machine_state=MachineState.RUNNING)


class _StubVisionEngine:
    name = "stub-vision"
    version = "1"

    def __init__(self, defect_score: float) -> None:
        self._defect_score = defect_score

    def predict(self, image: np.ndarray) -> InferenceOutput:
        return InferenceOutput(class_scores={"GOOD": 1 - self._defect_score, "DEFECT": self._defect_score},
                                timings_ms={"inference": 0.1})


class _CrashingVisionEngine:
    name = "crashing"
    version = "1"

    def predict(self, image: np.ndarray) -> InferenceOutput:
        raise RuntimeError("model backend crashed")


def _frame() -> Frame:
    return Frame(image=np.zeros((16, 16, 3), dtype=np.uint8), seq=0, captured_mono_ms=0, source="test")


def _vision(defect_score: float) -> VisionStageConfig:
    return VisionStageConfig(engine=_StubVisionEngine(defect_score), roi=ROI, thresholds=THRESHOLDS, model=MODEL)


def _ocr(text: str, confidence: float = 0.9) -> tuple[OcrStageConfig, FixtureOcrEngine]:
    engine = FixtureOcrEngine()
    engine.set_next_output(OcrOutput(raw_text=text, confidence=confidence))
    config = OcrStageConfig(engine=engine, preprocess=PreprocessConfig(roi=None, target_size=(64, 32)),
                             label_config=LabelValidationConfig(min_confidence=0.5),
                             reference_date=date(2026, 1, 1))
    return config, engine


def _decision_engine() -> DecisionEngine:
    return DecisionEngine(DecisionPolicy(deadline_ms=300))


def test_vision_only_good() -> None:
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=_vision(0.02), ocr=None,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ()
    assert trace.outcome is PipelineOutcome.GOOD
    assert trace.verdict_command is not None
    assert trace.verdict_command.verdict.value == "GOOD"


def test_vision_only_defect() -> None:
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=_vision(0.98), ocr=None,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert trace.outcome is PipelineOutcome.DEFECT


def test_ocr_only_good() -> None:
    ocr_config, _ = _ocr("EXP 2026-06-01", confidence=0.95)
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=None, ocr=ocr_config,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ()
    assert trace.label is not None
    assert trace.outcome is PipelineOutcome.GOOD


def test_ocr_only_expired_is_defect() -> None:
    ocr_config, _ = _ocr("EXP 2020-01-01", confidence=0.95)
    trace, _ = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=None, ocr=ocr_config,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert trace.outcome is PipelineOutcome.DEFECT


def test_vision_good_ocr_defect_any_defect_wins() -> None:
    ocr_config, _ = _ocr("EXP 2020-01-01", confidence=0.95)
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=_vision(0.02), ocr=ocr_config,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ()
    assert trace.outcome is PipelineOutcome.DEFECT
    assert trace.inspection is not None and trace.label is not None


def test_no_frame_is_not_a_subsystem_failure() -> None:
    """A FrameSource that simply has nothing new (returns None) is not a failure -- both
    frame-dependent channels are skipped, and this is reported as NO_DECISION, not degraded."""
    ocr_config, _ = _ocr("EXP 2026-06-01", confidence=0.95)
    trace, failed = run_product_cycle(
        "1-0", frame=None, cell_state=IDLE_STATE, vision=_vision(0.02), ocr=ocr_config,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ()  # "no frame" is not a subsystem failure, just nothing to inspect
    assert trace.inspection is None
    assert trace.label is None  # OCR also needs the frame; both channels simply have nothing to see
    assert trace.outcome is PipelineOutcome.NO_DECISION


def test_vision_engine_crash_is_reported_as_failed_not_fabricated() -> None:
    vision = VisionStageConfig(engine=_CrashingVisionEngine(), roi=ROI, thresholds=THRESHOLDS, model=MODEL)
    ocr_config, _ = _ocr("EXP 2026-06-01", confidence=0.95)
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=vision, ocr=ocr_config,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ("vision",)
    assert trace.inspection is None
    assert trace.label is not None
    assert trace.outcome is PipelineOutcome.GOOD  # OCR alone still produced a real decision


def test_no_channel_configured_is_no_decision_not_a_failure() -> None:
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=IDLE_STATE, vision=None, ocr=None,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ()
    assert trace.outcome is PipelineOutcome.NO_DECISION
    assert trace.verdict_command is None


def test_safety_gate_denies_before_running_any_channel() -> None:
    latched = CellStateSnapshot(machine_state=MachineState.ESTOP)
    trace, failed = run_product_cycle(
        "1-0", frame=_frame(), cell_state=latched, vision=_vision(0.02), ocr=None,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert failed == ()
    assert trace.outcome is PipelineOutcome.SAFETY_DENIED
    assert trace.denial_reason == "CELL_LATCHED_ESTOP"
    assert trace.inspection is None
    assert trace.verdict_command is None


def test_unknown_cell_state_denies_fail_closed() -> None:
    trace, _ = run_product_cycle(
        "1-0", frame=_frame(), cell_state=None, vision=_vision(0.02), ocr=None,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert trace.outcome is PipelineOutcome.SAFETY_DENIED
    assert trace.denial_reason == "CELL_STATE_UNKNOWN"


def test_running_state_allows_processing() -> None:
    trace, _ = run_product_cycle(
        "1-0", frame=_frame(), cell_state=RUNNING_STATE, vision=_vision(0.02), ocr=None,
        decision_engine=_decision_engine(), detected_at_mono_ms=0, now_mono_ms=40,
    )
    assert trace.outcome is PipelineOutcome.GOOD
