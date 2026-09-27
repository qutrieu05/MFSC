"""Tests for msfc.domain.inspection and msfc.domain.commands."""

from __future__ import annotations

import pytest

from msfc.core.errors import DomainError
from msfc.domain import (
    CommandAck,
    CommandResult,
    ControlCommand,
    DecisionRecord,
    InspectionResult,
    ModelInfo,
    RawVerdict,
    Verdict,
    VerdictCommand,
)
from msfc.domain.enums import CommandAction, MachineState


# --------------------------------------------------------------------------- InspectionResult
def _model() -> ModelInfo:
    return ModelInfo(name="classic_cv_baseline", version="0.1.0", backend="opencv")


def test_inspection_result_happy_path() -> None:
    result = InspectionResult(
        product_id="1-1", verdict=RawVerdict.DEFECT, confidence=0.87, model=_model(),
        timings_ms={"inference": 12.5, "total": 20.0},
    )
    assert result.timings_ms["total"] == 20.0


def test_inspection_result_requires_total_timing() -> None:
    with pytest.raises(DomainError, match="total"):
        InspectionResult(product_id="1-1", verdict=RawVerdict.GOOD, confidence=0.5, model=_model(),
                          timings_ms={"inference": 5.0})


def test_inspection_result_rejects_confidence_out_of_range() -> None:
    with pytest.raises(DomainError, match="confidence"):
        InspectionResult(product_id="1-1", verdict=RawVerdict.GOOD, confidence=1.5, model=_model(),
                          timings_ms={"total": 1.0})


def test_inspection_result_rejects_negative_timing() -> None:
    with pytest.raises(DomainError, match="timings_ms"):
        InspectionResult(product_id="1-1", verdict=RawVerdict.GOOD, confidence=0.5, model=_model(),
                          timings_ms={"total": -1.0})


def test_model_info_rejects_empty_name() -> None:
    with pytest.raises(DomainError):
        ModelInfo(name="", version="1")


# --------------------------------------------------------------------------- DecisionRecord
def test_decision_record_happy_path() -> None:
    rec = DecisionRecord(
        decision_id="d-1-1", product_id="1-1", final_verdict=Verdict.DEFECT,
        reason_codes=("VISION_DEFECT",), rules_version="rules-0.1",
        late=False, inputs={"vision": {"verdict": "DEFECT"}},
    )
    assert rec.final_verdict is Verdict.DEFECT


def test_decision_record_requires_at_least_one_reason_code() -> None:
    with pytest.raises(DomainError, match="reason_codes"):
        DecisionRecord(decision_id="d-1", product_id="1-1", final_verdict=Verdict.GOOD,
                        reason_codes=(), rules_version="r1", late=False)


def test_decision_record_rejects_more_than_eight_reason_codes() -> None:
    with pytest.raises(DomainError, match="8"):
        DecisionRecord(decision_id="d-1", product_id="1-1", final_verdict=Verdict.GOOD,
                        reason_codes=tuple(f"R{i}" for i in range(9)), rules_version="r1", late=False)


# --------------------------------------------------------------------------- VerdictCommand
def test_verdict_command_happy_path() -> None:
    cmd = VerdictCommand(product_id="1-1", verdict=Verdict.GOOD, decision_id="d-1", reason_codes=("OK",))
    assert cmd.confidence is None


def test_verdict_command_rejects_empty_reason_codes() -> None:
    with pytest.raises(DomainError):
        VerdictCommand(product_id="1-1", verdict=Verdict.GOOD, decision_id="d-1", reason_codes=())


# --------------------------------------------------------------------------- ControlCommand
def test_control_command_start() -> None:
    cmd = ControlCommand(cmd_id="c1", action=CommandAction.START, source="cli")
    assert cmd.params == {}


def test_control_command_set_speed_requires_param() -> None:
    with pytest.raises(DomainError, match="speed_pct"):
        ControlCommand(cmd_id="c1", action=CommandAction.SET_SPEED, source="cli")


def test_control_command_set_speed_happy_path() -> None:
    cmd = ControlCommand(cmd_id="c1", action=CommandAction.SET_SPEED, source="cli",
                          params={"speed_pct": 42.0})
    assert cmd.params["speed_pct"] == 42.0


def test_control_command_set_speed_out_of_range() -> None:
    with pytest.raises(DomainError, match="speed_pct"):
        ControlCommand(cmd_id="c1", action=CommandAction.SET_SPEED, source="cli",
                        params={"speed_pct": 101.0})


# --------------------------------------------------------------------------- CommandAck
def test_command_ack_accepted_needs_no_reason() -> None:
    ack = CommandAck(cmd_id="c1", action="start", result=CommandResult.ACCEPTED)
    assert ack.reason is None


def test_command_ack_rejected_requires_reason() -> None:
    with pytest.raises(DomainError, match="reason"):
        CommandAck(cmd_id="c1", action="reset", result=CommandResult.REJECTED)


def test_command_ack_rejected_with_reason_and_state() -> None:
    ack = CommandAck(cmd_id="c1", action="reset", result=CommandResult.REJECTED,
                      reason="estop_latched", state_after=MachineState.ESTOP)
    assert ack.state_after is MachineState.ESTOP
