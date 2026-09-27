"""Tests for msfc.decision (DecisionEngine, DecisionPolicy) — FR-DEC-01..04."""

from __future__ import annotations

import pytest

from msfc.core.errors import DecisionError
from msfc.decision import DecisionEngine, DecisionPolicy
from msfc.domain import InspectionResult, ModelInfo, RawVerdict, Verdict


def _insp(product_id="1-1", verdict=RawVerdict.GOOD, model_name="vision", confidence=0.9) -> InspectionResult:
    return InspectionResult(
        product_id=product_id, verdict=verdict, confidence=confidence,
        model=ModelInfo(name=model_name, version="0.1"), timings_ms={"total": 5.0},
    )


# --------------------------------------------------------------------------- DecisionPolicy
@pytest.mark.parametrize("kwargs,match", [
    ({"uncertain_verdict": RawVerdict.UNCERTAIN}, "uncertain_verdict"),
    ({"deadline_ms": 0}, "deadline_ms"),
    ({"deadline_ms": -1}, "deadline_ms"),
    ({"rules_version": "  "}, "rules_version"),
])
def test_policy_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(DecisionError, match=match):
        DecisionPolicy(**kwargs)


def test_policy_defaults() -> None:
    policy = DecisionPolicy()
    assert policy.uncertain_verdict is RawVerdict.DEFECT
    assert policy.deadline_ms == 300


# --------------------------------------------------------------------------- combine rules
def test_all_good_channels_yield_good() -> None:
    engine = DecisionEngine()
    record = engine.decide("1-1", [_insp(verdict=RawVerdict.GOOD)],
                            detected_at_mono_ms=1000, now_mono_ms=1100)
    assert record.final_verdict is Verdict.GOOD
    assert "ALL_CHANNELS_GOOD" in record.reason_codes


def test_any_defect_channel_wins_over_good() -> None:
    engine = DecisionEngine()
    inspections = [
        _insp(model_name="vision", verdict=RawVerdict.GOOD),
        _insp(model_name="ocr", verdict=RawVerdict.DEFECT),
    ]
    record = engine.decide("1-1", inspections, detected_at_mono_ms=0, now_mono_ms=50)
    assert record.final_verdict is Verdict.DEFECT
    assert "OCR_DEFECT" in record.reason_codes


def test_uncertain_default_policy_resolves_to_defect() -> None:
    engine = DecisionEngine()  # default policy: uncertain -> DEFECT
    record = engine.decide("1-1", [_insp(verdict=RawVerdict.UNCERTAIN)],
                            detected_at_mono_ms=0, now_mono_ms=10)
    assert record.final_verdict is Verdict.DEFECT
    assert "UNCERTAIN_POLICY_DEFECT" in record.reason_codes
    assert "VISION_UNCERTAIN" in record.reason_codes


def test_uncertain_policy_can_be_configured_to_good() -> None:
    engine = DecisionEngine(DecisionPolicy(uncertain_verdict=RawVerdict.GOOD))
    record = engine.decide("1-1", [_insp(verdict=RawVerdict.UNCERTAIN)],
                            detected_at_mono_ms=0, now_mono_ms=10)
    assert record.final_verdict is Verdict.GOOD
    assert "UNCERTAIN_POLICY_GOOD" in record.reason_codes


def test_defect_wins_over_uncertain_from_another_channel() -> None:
    engine = DecisionEngine()
    inspections = [
        _insp(model_name="vision", verdict=RawVerdict.UNCERTAIN),
        _insp(model_name="ocr", verdict=RawVerdict.DEFECT),
    ]
    record = engine.decide("1-1", inspections, detected_at_mono_ms=0, now_mono_ms=10)
    assert record.final_verdict is Verdict.DEFECT
    assert "OCR_DEFECT" in record.reason_codes
    assert not any("UNCERTAIN" in code for code in record.reason_codes)


# --------------------------------------------------------------------------- late flag (FR-DEC-02)
def test_decision_within_deadline_is_not_late() -> None:
    engine = DecisionEngine(DecisionPolicy(deadline_ms=300))
    record = engine.decide("1-1", [_insp()], detected_at_mono_ms=1000, now_mono_ms=1250)
    assert record.late is False
    assert "DECISION_LATE" not in record.reason_codes


def test_decision_past_deadline_is_late() -> None:
    engine = DecisionEngine(DecisionPolicy(deadline_ms=300))
    record = engine.decide("1-1", [_insp()], detected_at_mono_ms=1000, now_mono_ms=1301)
    assert record.late is True
    assert "DECISION_LATE" in record.reason_codes


def test_decision_exactly_at_deadline_is_not_late() -> None:
    engine = DecisionEngine(DecisionPolicy(deadline_ms=300))
    record = engine.decide("1-1", [_insp()], detected_at_mono_ms=1000, now_mono_ms=1300)
    assert record.late is False


# --------------------------------------------------------------------------- input validation
def test_decide_rejects_empty_inspections() -> None:
    engine = DecisionEngine()
    with pytest.raises(DecisionError, match="at least one"):
        engine.decide("1-1", [], detected_at_mono_ms=0, now_mono_ms=0)


def test_decide_rejects_mismatched_product_id() -> None:
    engine = DecisionEngine()
    with pytest.raises(DecisionError, match="does not match"):
        engine.decide("1-1", [_insp(product_id="1-2")], detected_at_mono_ms=0, now_mono_ms=0)


def test_decide_rejects_clock_going_backwards() -> None:
    engine = DecisionEngine()
    with pytest.raises(DecisionError, match="must not be before"):
        engine.decide("1-1", [_insp()], detected_at_mono_ms=1000, now_mono_ms=999)


# --------------------------------------------------------------------------- record contents
def test_decision_id_is_deterministic_from_product_id() -> None:
    engine = DecisionEngine()
    record = engine.decide("7-42", [_insp(product_id="7-42")], detected_at_mono_ms=0, now_mono_ms=1)
    assert record.decision_id == "d-7-42"


def test_decision_record_captures_input_summary() -> None:
    engine = DecisionEngine()
    record = engine.decide("1-1", [_insp(verdict=RawVerdict.DEFECT, confidence=0.77)],
                            detected_at_mono_ms=0, now_mono_ms=1)
    assert record.inputs["vision"] == {"verdict": "DEFECT", "confidence": 0.77}


def test_decision_record_rules_version_matches_policy() -> None:
    engine = DecisionEngine(DecisionPolicy(rules_version="rules-9.9"))
    record = engine.decide("1-1", [_insp()], detected_at_mono_ms=0, now_mono_ms=1)
    assert record.rules_version == "rules-9.9"


# --------------------------------------------------------------------------- to_verdict_command
def test_to_verdict_command_round_trips_the_record() -> None:
    engine = DecisionEngine()
    record = engine.decide("1-1", [_insp(verdict=RawVerdict.DEFECT)], detected_at_mono_ms=0, now_mono_ms=1)
    cmd = engine.to_verdict_command(record, confidence=0.88)
    assert cmd.product_id == "1-1"
    assert cmd.verdict is Verdict.DEFECT
    assert cmd.decision_id == record.decision_id
    assert cmd.reason_codes == record.reason_codes
    assert cmd.confidence == 0.88
