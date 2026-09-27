"""Tests for msfc.domain.events."""

from __future__ import annotations

import pytest

from msfc.core.errors import DomainError
from msfc.domain import ProductDetectedEvent, ProductSortedEvent, SortAction, SortReason, StateChangedEvent
from msfc.domain.enums import MachineState


# --------------------------------------------------------------------------- ProductDetectedEvent
def test_product_detected_happy_path() -> None:
    evt = ProductDetectedEvent(product_id="7-42", t_detect_mono_ms=1000, speed_setpoint_pct=50.0)
    assert evt.sensor == "S1"


@pytest.mark.parametrize("bad_id", ["742", "7-", "-42", "7_42", "abc-1", ""])
def test_product_detected_rejects_bad_product_id(bad_id: str) -> None:
    with pytest.raises(DomainError, match="product_id"):
        ProductDetectedEvent(product_id=bad_id, t_detect_mono_ms=0)


def test_product_detected_rejects_negative_timestamp() -> None:
    with pytest.raises(DomainError, match="t_detect_mono_ms"):
        ProductDetectedEvent(product_id="1-1", t_detect_mono_ms=-5)


def test_product_detected_rejects_speed_out_of_range() -> None:
    with pytest.raises(DomainError, match="speed_setpoint_pct"):
        ProductDetectedEvent(product_id="1-1", t_detect_mono_ms=0, speed_setpoint_pct=150.0)


# --------------------------------------------------------------------------- ProductSortedEvent
def _sorted(**overrides) -> ProductSortedEvent:
    defaults = dict(
        product_id="7-42", action=SortAction.REJECTED, reason=SortReason.VERDICT_DEFECT,
        verdict_received=True, t_detect_mono_ms=1000, t_s2_mono_ms=1200, t_verdict_rx_mono_ms=1100,
    )
    defaults.update(overrides)
    return ProductSortedEvent(**defaults)


def test_product_sorted_computes_latency_and_margin() -> None:
    evt = _sorted()
    assert evt.latency_detect_to_verdict_ms == 100
    assert evt.margin_ms == 100


def test_product_sorted_no_decision_has_none_latency_and_margin() -> None:
    evt = _sorted(verdict_received=False, t_verdict_rx_mono_ms=None, reason=SortReason.NO_DECISION)
    assert evt.latency_detect_to_verdict_ms is None
    assert evt.margin_ms is None


def test_product_sorted_verdict_received_true_requires_timestamp() -> None:
    with pytest.raises(DomainError, match="t_verdict_rx_mono_ms is missing"):
        _sorted(t_verdict_rx_mono_ms=None)


def test_product_sorted_verdict_received_false_forbids_timestamp() -> None:
    with pytest.raises(DomainError, match="t_verdict_rx_mono_ms is set"):
        _sorted(verdict_received=False, reason=SortReason.NO_DECISION)


def test_product_sorted_s2_before_detect_is_rejected() -> None:
    with pytest.raises(DomainError, match="t_s2_mono_ms"):
        _sorted(t_detect_mono_ms=2000, t_s2_mono_ms=1000, t_verdict_rx_mono_ms=1500)


def test_product_sorted_negative_margin_is_representable_not_rejected() -> None:
    """A late verdict (margin <= 0) is a real, observable condition (F032) — the dataclass
    must allow constructing it so the caller can detect and report DECISION_LATE; only the
    physically impossible s2-before-detect case is rejected."""
    evt = _sorted(t_detect_mono_ms=1000, t_verdict_rx_mono_ms=1300, t_s2_mono_ms=1200)
    assert evt.margin_ms == -100


# --------------------------------------------------------------------------- StateChangedEvent
def test_state_changed_happy_path() -> None:
    evt = StateChangedEvent(from_state=MachineState.IDLE, to_state=MachineState.STARTING, cause="cmd:start")
    assert evt.cause == "cmd:start"


def test_state_changed_rejects_empty_cause() -> None:
    with pytest.raises(DomainError, match="cause"):
        StateChangedEvent(from_state=MachineState.IDLE, to_state=MachineState.FAULT, cause="   ")
