"""Tests for msfc.contracts.validation.PayloadValidator using the real contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from msfc.core.errors import PayloadInvalidError
from msfc.contracts import ContractRegistry, PayloadValidator, build_envelope


@pytest.fixture(scope="module")
def registry(repo_root: Path) -> ContractRegistry:
    return ContractRegistry.load(repo_root / "contracts")


@pytest.fixture(scope="module")
def validator(registry: ContractRegistry) -> PayloadValidator:
    return PayloadValidator(registry)


def _detected_envelope(**data_overrides) -> dict:
    data = {"product_id": "7-42", "sensor": "S1", "t_detect_mono_ms": 1000}
    data.update(data_overrides)
    return build_envelope(schema="product_detected.v1", device_id="esp32-cc01",
                           seq=1, mono_ms=1000, data=data, boot_id=7)


# --------------------------------------------------------------------------- happy path
def test_valid_envelope_passes(validator: PayloadValidator) -> None:
    validator.validate_for_topic("conveyor.event.product_detected", _detected_envelope())


def test_valid_unknown_topic_helper_passes(validator: PayloadValidator) -> None:
    validator.validate_unknown_topic(
        "factory/line01/conveyor/esp32-cc01/event/product_detected", _detected_envelope()
    )


# --------------------------------------------------------------------------- envelope shape errors
def test_missing_required_envelope_field_is_rejected(validator: PayloadValidator) -> None:
    envelope = _detected_envelope()
    del envelope["mono_ms"]
    with pytest.raises(PayloadInvalidError, match="envelope shape invalid"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


def test_extra_envelope_field_is_rejected(validator: PayloadValidator) -> None:
    envelope = _detected_envelope()
    envelope["unexpected"] = 1
    with pytest.raises(PayloadInvalidError, match="envelope shape invalid"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


def test_non_dict_envelope_is_rejected(validator: PayloadValidator) -> None:
    with pytest.raises(PayloadInvalidError, match="must be a JSON object"):
        validator.validate_shape("not-a-dict")  # type: ignore[arg-type]


def test_bad_device_id_pattern_is_rejected(validator: PayloadValidator) -> None:
    envelope = _detected_envelope()
    envelope["device_id"] = "BAD ID!"
    with pytest.raises(PayloadInvalidError, match="envelope shape invalid"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


# --------------------------------------------------------------------------- data errors
def test_schema_mismatch_for_topic_is_rejected(validator: PayloadValidator) -> None:
    envelope = build_envelope(schema="fault.v1", device_id="esp32-cc01", seq=1, mono_ms=1,
                               data={"code": "F010", "name": "COMM_LOSS_EDGE", "severity": "FAULT",
                                     "event": "RAISED", "latched": True})
    with pytest.raises(PayloadInvalidError, match="expects 'product_detected.v1'"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


def test_data_missing_required_field_is_rejected(validator: PayloadValidator) -> None:
    envelope = _detected_envelope()
    del envelope["data"]["sensor"]
    with pytest.raises(PayloadInvalidError, match="data invalid"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


def test_data_wrong_enum_value_is_rejected(validator: PayloadValidator) -> None:
    envelope = _detected_envelope(sensor="S2")  # schema restricts sensor to the constant "S1"
    with pytest.raises(PayloadInvalidError, match="data invalid"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


def test_data_bad_product_id_pattern_is_rejected(validator: PayloadValidator) -> None:
    envelope = _detected_envelope(product_id="not-a-valid-id")
    with pytest.raises(PayloadInvalidError, match="data invalid"):
        validator.validate_for_topic("conveyor.event.product_detected", envelope)


def test_unknown_topic_key_bubbles_up_as_contract_error(validator: PayloadValidator) -> None:
    from msfc.core.errors import ContractError
    with pytest.raises(ContractError, match="unknown topic key"):
        validator.validate_for_topic("no.such.topic", _detected_envelope())


def test_unknown_schema_name_is_reported_as_payload_invalid(validator: PayloadValidator) -> None:
    envelope = build_envelope(schema="does_not_exist.v1", device_id="dev01", seq=0, mono_ms=0, data={})
    with pytest.raises(PayloadInvalidError, match="unavailable"):
        validator.validate_unknown_topic("factory/line01/conveyor/dev01/status", envelope)


def test_command_ack_reject_reason_required_by_schema(validator: PayloadValidator) -> None:
    """Cross-check: cmd_ack.v1 itself doesn't enforce the reason-when-rejected rule (that is
    a domain-level invariant in msfc.domain.commands.CommandAck), but the schema does still
    require the base fields and constrains 'result' to the four known values."""
    envelope = build_envelope(schema="cmd_ack.v1", device_id="esp32-cc01", seq=0, mono_ms=0,
                               data={"cmd_id": "c1", "action": "reset", "result": "MAYBE"})
    with pytest.raises(PayloadInvalidError, match="data invalid"):
        validator.validate_unknown_topic("factory/line01/conveyor/esp32-cc01/ack", envelope)
